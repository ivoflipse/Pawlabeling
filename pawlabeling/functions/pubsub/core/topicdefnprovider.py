'''
This module contains several concrete classes that implement the 
ITopicDefnDeserializer interface. They all assume a Python class 
syntax format, but stored as a string, module file, or class object. 

:copyright: Copyright since 2006 by Oliver Schoenborn, all rights reserved.
:license: BSD, see LICENSE.txt for details.
'''


import os, re, inspect
from textwrap import TextWrapper, dedent

import policies
from topicargspec import topicArgsFromCallable
from topictreetraverser import TopicTreeTraverser
from itopicdefnprovider import ITopicDefnProvider

# method name assumed to represent Topic Message Data Specification
SPEC_METHOD_NAME = 'msgDataSpec'


class ITopicDefnDeserializer:
    '''
    All functionality to convert a topic tree representation into a
    set of topic definitions that can be used by a topic definition
    provider.
    '''

    class TopicDefn:
        '''Encapsulate date for a topic definition. Returned by
        getNextTopic().'''

        def __init__(self, nameTuple, description, argsDocs, required):
            self.nameTuple = nameTuple
            self.description = description
            self.argsDocs = argsDocs
            self.required = required

        def isComplete(self):
            return (self.description is not None) and (self.argsDocs is not None)

    def getTreeDoc(self):
        '''Get the documentation for the topic tree. This will be
        interpreted differently based on the type of definition provider. '''
        raise NotImplementedError

    def getNextTopic(self):
        '''Override this to provide the next topic definition available
        from the data. The return must be an instance of TopicDefn.'''
        raise NotImplementedError

    def doneIter(self):
        '''This will be called automatically by the definition provider once
        it considers the iteration completed. Override this only if your
        deserializer needs to do something, such as close a file.
        '''
        pass

    def resetIter(self):
        '''May be called by the definition provider if needs to
        restart the iteration. Override this only if something
        special must be done such as resetting a file point to
        beginning etc. '''
        pass


class TopicDefnDeserialClass(ITopicDefnDeserializer):
    '''
    Interpret a class tree as a topic definition tree. The class name is the
    topic name, its doc string is its description. A method called the same 
    as SPEC_METHOD_NAME is inpsected to infer the optional and required
    message arguments that all listeners must accept. The doc string of that
    method is parsed to extract the description for each argument.
    '''

    def __init__(self, pyClassObj=None):
        '''If pyClassObj is given, it is a class that contains nested
        classes defining root topics; the root topics contain nested
        classes defining subtopics; etc. Hence the init calls
        addDefnFromClassObj() on each nested class found in pyClassObj. '''
        self.__rootTopics = []
        self.__iterStarted = False
        self.__nextTopic = iter(self.__rootTopics)
        self.__rootDoc = None

        if pyClassObj is not None:
            self.__rootDoc = pyClassObj.__doc__
            topicClasses = self.__getTopicClasses(pyClassObj)
            for topicName, pyClassObj in topicClasses:
                self.addDefnFromClassObj(pyClassObj)

    def getTreeDoc(self):
        '''Returns the first doc string that was found in the pyClassObj
        given to self. '''
        return self.__rootDoc

    def addDefnFromClassObj(self, pyClassObj):
        '''Use pyClassObj as a topic definition written using "Python classes".
        The class name is the topic name, assumed to be a root topic, and
        descends recursively down into nested classes. '''
        if self.__iterStarted:
            raise RuntimeError('addClassObj must be called before iteration started!')

        parentNameTuple = (pyClassObj.__name__, )
        if pyClassObj.__doc__ is not None:
            self.__rootTopics.append( (parentNameTuple, pyClassObj) )
            if self.__rootDoc is None:
                self.__rootDoc = pyClassObj.__doc__
        self.__findTopics(pyClassObj, parentNameTuple)
        # iterator is now out of sync, so reset it; obviously this would
        # screw up getNextTopic which is why we had to test for self.__iterStarted
        self.__nextTopic = iter(self.__rootTopics)

    def getNextTopic(self):
        '''Get next topic defined by this provider. Returns None when
        no topics are left. May call resetIter() to restart the iteration.'''
        self.__iterStarted = True
        try:
            topicNameTuple, topicClassObj = self.__nextTopic.next()
        except StopIteration:
            return None

        # ok get the info from class
        if hasattr(topicClassObj, SPEC_METHOD_NAME):
            protoListener = getattr(topicClassObj, SPEC_METHOD_NAME)
            argsDocs, required = topicArgsFromCallable(protoListener)
            if protoListener.__doc__:
                self.__setArgsDocsFromProtoDocs(argsDocs, protoListener.__doc__)
        else:
            # assume definition is implicitly that listener has no args
            argsDocs = {}
            required = ()
        desc = None
        if topicClassObj.__doc__:
            desc = dedent(topicClassObj.__doc__)
        return self.TopicDefn(topicNameTuple, desc, argsDocs, required)

    def resetIter(self):
        self.__iterStarted = False
        self.__nextTopic = iter(self.__rootTopics)

    def getDefinedTopics(self):
        return [nt for (nt, defn) in self.__rootTopics]

    def __findTopics(self, pyClassObj, parentNameTuple):
        assert not self.__iterStarted
        assert parentNameTuple
        assert pyClassObj.__name__ == parentNameTuple[-1]

        topicClasses = self.__getTopicClasses(pyClassObj, parentNameTuple)
        pyClassObj._topicNameStr = '.'.join(parentNameTuple)

        # make sure to update rootTopics BEFORE we recurse, so that toplevel
        # topics come first in the list
        for parentNameTuple2, topicClassObj in topicClasses:
            # we only keep track of topics that are documented, so that
            # multiple providers can co-exist without having to duplicate
            # information
            if topicClassObj.__doc__ is not None:
                self.__rootTopics.append( (parentNameTuple2, topicClassObj) )
            # now can find its subtopics
            self.__findTopics(topicClassObj, parentNameTuple2)

    def __getTopicClasses(self, pyClassObj, parentNameTuple=()):
        '''Returns a list of pairs, (topicNameTuple, memberClassObj)'''
        memberNames = dir(pyClassObj)
        topicClasses = []
        for memberName in memberNames:
            member = getattr(pyClassObj, memberName)
            if inspect.isclass( member ):
                topicNameTuple = parentNameTuple + (memberName,)
                topicClasses.append( (topicNameTuple, member) )
        return topicClasses

    def __setArgsDocsFromProtoDocs(self, argsDocs, protoDocs):
        PAT_ITEM_STR = r'\A-\s*' # hyphen and any number of blanks
        PAT_ARG_NAME = r'(?P<argName>\w*)'
        PAT_DOC_STR  = r'(?P<doc1>.*)'
        PAT_BLANK    = r'\s*'
        PAT_ITEM_SEP = r':'
        argNamePat = re.compile(
            PAT_ITEM_STR + PAT_ARG_NAME + PAT_BLANK + PAT_ITEM_SEP
            + PAT_BLANK + PAT_DOC_STR)
        protoDocs = dedent(protoDocs)
        lines = protoDocs.splitlines()
        argName = None
        namesFound = []
        for line in lines:
            match = argNamePat.match(line)
            if match:
                argName = match.group('argName')
                namesFound.append(argName)
                argsDocs[argName] = [match.group('doc1') ]
            elif argName:
                argsDocs[argName].append(line)

        for name in namesFound:
            argsDocs[name] = '\n'.join( argsDocs[name] )


class TopicDefnDeserialModule(ITopicDefnDeserializer):
    '''
    Deserialize a module containing source code defining a topic tree.
    This loads the module and finds all class definitions in it (at
    module level that is) and uses a TopicDefnDeserialClass to
    deserialize each one into a topic definition.
    '''

    def __init__(self, moduleName, searchPath=None):
        '''Load the given named module, searched for in searchPath or, if not
        specified, in sys.path. The top-level classes will be assumed to be
        topic definitions with a doc string and a message data specification
        method as described in TopicDefnDeserialClass'.
        '''
        import imp2
        module = imp2.load_module(moduleName, searchPath)
        self.__classDeserial = TopicDefnDeserialClass(module)

    def getTreeDoc(self):
        return self.__classDeserial.getTreeDoc()
        #return self.__moduleDoc
    
    def getNextTopic(self):
        return self.__classDeserial.getNextTopic()

    def doneIter(self):
        self.__classDeserial.doneIter()

    def resetIter(self):
        self.__classDeserial.resetIter()

    def getDefinedTopics(self):
        return self.__classDeserial.getDefinedTopics()


class TopicDefnDeserialString(ITopicDefnDeserializer):
    '''
    Deserialize a string containing source code defining a topic tree.
    This just saves the string into a temporary file created in os.getcwd(), 
    and the rest is delegated to TopicDefnDeserialModule. The temporary
    file (module) is deleted (as well as its byte-compiled version)
    when the doneIter() method is called.
    '''

    def __init__(self, source):
        def createTmpModule():
            moduleNamePre = 'tmp_export_topics_'
            import os, tempfile
            creationDir = os.getcwd()
            fileID, path = tempfile.mkstemp('.py', moduleNamePre, dir=creationDir)
            stringFile = os.fdopen(fileID, 'w')
            stringFile.write( dedent(source) )
            stringFile.close()
            return path, [creationDir]

        self.__filename, searchPath = createTmpModule()
        moduleName = os.path.splitext( os.path.basename(self.__filename) )[0]
        self.__modDeserial = TopicDefnDeserialModule(moduleName, searchPath)

    def getTreeDoc(self):
        return self.__modDeserial.getTreeDoc()

    def getNextTopic(self):
        return self.__modDeserial.getNextTopic()

    def doneIter(self):
        self.__modDeserial.doneIter()
        # remove the temporary module and its compiled version (*.pyc)
        os.remove(self.__filename)
        os.remove(self.__filename + 'c')

    def resetIter(self):
        self.__modDeserial.resetIter()

    def getDefinedTopics(self):
        return self.__modDeserial.getDefinedTopics()


TOPIC_TREE_FROM_MODULE = 'module'
TOPIC_TREE_FROM_STRING = 'string'
TOPIC_TREE_FROM_CLASS  = 'class'


class TopicDefnProvider(ITopicDefnProvider):
    '''
    Default implementation of the ITopicDefnProvider API. This
    implementation accepts several formats for the source data
    and delegates to suitable parser that knows how to convert
    source data into a topic definition.

    You can create your own topic definition provider classes,
    for formats (say, XML) not supported by TopicDefnProvider.
    See also pub.addTopicDefnProvider().
    '''

    typeRegistry = {}

    class UnrecognizedImportFormat(ValueError): pass
    
    def __init__(self, source, format, **providerKwargs):
        if format not in self.typeRegistry:
            raise self.UnrecognizedImportFormat()
        providerClassObj = self.typeRegistry[format]
        provider = providerClassObj(source, **providerKwargs)
        self.__topicDefns = {}
        self.__treeDocs = provider.getTreeDoc()
        try:
            topicDefn = provider.getNextTopic()
            while topicDefn is not None:
                self.__topicDefns[topicDefn.nameTuple] = topicDefn
                topicDefn = provider.getNextTopic()
        finally:
            provider.doneIter()

    def getDefn(self, topicNameTuple):
        desc, spec = None, None
        defn = self.__topicDefns.get(topicNameTuple, None)
        if defn is not None:
            assert defn.isComplete()
            desc = defn.description
            spec = self.ArgSpecGiven(defn.argsDocs, defn.required)
        return desc, spec

    def topicNames(self):
        return self.__topicDefns.iterkeys()

    def getTreeDoc(self):
        return self.__treeDocs


def registerTypeForImport(typeName, providerClassObj):
    TopicDefnProvider.typeRegistry[typeName] = providerClassObj

registerTypeForImport(TOPIC_TREE_FROM_MODULE, TopicDefnDeserialModule)
registerTypeForImport(TOPIC_TREE_FROM_STRING, TopicDefnDeserialString)
registerTypeForImport(TOPIC_TREE_FROM_CLASS,  TopicDefnDeserialClass)


def _backupIfExists(filename, bak):
    import os, shutil
    if os.path.exists(filename):
        backupName = '%s.%s' % (filename, bak)
        shutil.copy(filename, backupName)


defaultTopicTreeSpecHeader = \
"""
Topic tree for application.
Used via pub.addTopicDefnProvider(thisModuleName).
"""

defaultTopicTreeSpecFooter = \
"""\
# End of topic tree definition. Note that application may load
# more than one definitions provider.
"""


def exportTopicTreeSpec(moduleName = None, rootTopic=None, bak='bak', moduleDoc=None):
    '''Export the topic tree rooted at rootTopic to module (.py) file. This file 
    will contain a nested class hierarchy representing the topic tree. Returns a
    string representing the contents of the file. Parameters:

        - If moduleName is given, the topic tree is written to moduleName.py in
          os.getcwd() (the file is overwritten). If bak is None, the module file
          is not backed up.
        - If rootTopic is specified, the export only traverses tree from 
          corresponding topic. Otherwise, complete tree, using 
          pub.getDefaultTopicTreeRoot() as starting  point.
        - The moduleDoc is the doc string for the module ie topic tree.
    '''

    if rootTopic is None:
        from pubsub import pub
        rootTopic = pub.getDefaultTopicTreeRoot()
    elif isinstance(rootTopic, (str, unicode)):
        from pubsub import pub
        rootTopic = pub.getTopic(rootTopic)

    # create exporter
    if moduleName is None:
        from StringIO import StringIO
        capture = StringIO()
        TopicTreeSpecPrinter(rootTopic, fileObj=capture, treeDoc=moduleDoc)
        return capture.getvalue()

    else:
        filename = '%s.py' % moduleName
        if bak:
            _backupIfExists(filename, bak)
        moduleFile = file(filename, 'w')
        try:
            TopicTreeSpecPrinter(rootTopic, fileObj=moduleFile, treeDoc=moduleDoc)
        finally:
            moduleFile.close()

##############################################################

def _toDocString(msg):
    if not msg:
        return msg
    if msg.startswith("'''") or msg.startswith('"""'):
        return msg
    return "'''\n%s\n'''" % msg.strip()


class TopicTreeSpecPrinter:
    '''
    Function class to print the topic tree using the Python class
    syntax. If printed to a module, it can then be imported, 
    given to pub.addTopicDefnProvider(), etc. 
    The printout can be sent to any file object (object that has a
    write() method).
    '''

    INDENT_CH = ' '
    #INDENT_CH = '.'

    def __init__(self, rootTopic=None, fileObj=None, width=70, indentStep=4, 
        treeDoc = defaultTopicTreeSpecHeader, footer = defaultTopicTreeSpecFooter):
        '''For formatting, can specify the width of output, the indent step, the 
        header and footer to print to override defaults. The destination is fileObj;
        if none is given, then sys.stdout is used. If rootTopic is given(), calls
        writeAll(rootTopic) at end of __init__.'''
        self.__traverser = TopicTreeTraverser(self)

        import sys
        fileObj = fileObj or sys.stdout

        self.__destination = fileObj
        self.__output = []
        self.__header = _toDocString(treeDoc)
        self.__footer = footer
        self.__lastWasAll = False # True when last topic done was the ALL_TOPICS

        self.__width   = width
        self.__wrapper = TextWrapper(width)
        self.__indentStep = indentStep
        self.__indent  = 0

        args = dict(width=width, indentStep=indentStep, treeDoc=treeDoc,
                    footer=footer, fileObj=fileObj)
        def fmItem(argName, argVal):
            if isinstance(argVal, (str, unicode)):
                MIN_OFFSET = 5
                lenAV = width - MIN_OFFSET - len(argName)
                if lenAV > 0:
                    argVal = `argVal[:lenAV] + '...'`
            elif argName == 'fileObj':
                argVal = fileObj.__class__.__name__
            return '# - %s: %s' % (argName, argVal)
        fmtArgs = [fmItem(argName, argVal) for (argName, argVal) in args.iteritems()]
        self.__comment = [
            '# Automatically generated by %s(**kwargs).' % self.__class__.__name__,
            '# The kwargs were:',
        ]
        self.__comment.extend(fmtArgs)
        self.__comment.extend(['']) # two empty line after comment
        
        if rootTopic is not None:
            self.writeAll(rootTopic)

    def getOutput(self):
        '''Each line that was sent to fileObj was saved in a list; returns a 
        string which is '\n'.join(list).'''
        return '\n'.join( self.__output )

    def writeAll(self, topicObj):
        '''Traverse each topic of topic tree, starting at topicObj, printing
        each topic definition as the tree gets traversed. '''
        self.__traverser.traverse(topicObj)

    def _accept(self, topicObj):
        # accept every topic
        return True

    def _startTraversal(self):
        # output comment
        self.__wrapper.initial_indent = '# '
        self.__wrapper.subsequent_indent = self.__wrapper.initial_indent
        self.__output.extend( self.__comment )

        # output header:
        if self.__header:
            self.__output.extend([''])
            self.__output.append(self.__header)
            self.__output.extend([''])

    def _doneTraversal(self):
        if self.__footer:
            self.__output.append('')
            self.__output.append('')
            self.__output.append(self.__footer)

        if self.__destination is not None:
            self.__destination.write(self.getOutput())

    def _onTopic(self, topicObj):
        '''This gets called for each topic. Print as per specified content.'''
        # don't print root of tree, it is the ALL_TOPICS builtin topic
        if topicObj.isAll():
            self.__lastWasAll = True
            return
        self.__lastWasAll = False

        self.__output.append( '' ) # empty line
        # topic name
        self.__wrapper.width = self.__width
        head = 'class %s:' % topicObj.getNodeName()
        self.__formatItem(head)

        # each extra content (assume constructor verified that chars are valid)
        self.__printTopicDescription(topicObj)
        if policies.msgDataProtocol != 'arg1':
            self.__printTopicArgSpec(topicObj)

    def _startChildren(self):
        '''Increase the indent'''
        if not self.__lastWasAll:
            self.__indent += self.__indentStep

    def _endChildren(self):
        '''Decrease the indent'''
        if not self.__lastWasAll:
           self.__indent -= self.__indentStep

    def __printTopicDescription(self, topicObj):
        if topicObj.getDescription():
            extraIndent = self.__indentStep
            self.__formatItem("'''", extraIndent)
            self.__formatItem( topicObj.getDescription(), extraIndent )
            self.__formatItem("'''", extraIndent)

    def __printTopicArgSpec(self, topicObj):
        extraIndent = self.__indentStep

        # generate the listener protocol
        reqdArgs, optArgs = topicObj.getArgs()
        argsStr = []
        if reqdArgs:
            argsStr.append( ", ".join(reqdArgs) )
        if optArgs:
            optStr = ', '.join([('%s=None' % arg) for arg in optArgs])
            argsStr.append(optStr)
        argsStr = ', '.join(argsStr)

        # print it only if there are args; ie if listener() don't print it
        if argsStr:
            # output a blank line and protocol
            self.__formatItem('\n', extraIndent)
            protoListener = 'def %s(%s):' % (SPEC_METHOD_NAME, argsStr)
            self.__formatItem(protoListener, extraIndent)

            # and finally, the args docs
            extraIndent += self.__indentStep
            self.__formatItem("'''", extraIndent)
            # but ignore the arg keys that are in parent args docs:
            parentMsgKeys = ()
            if topicObj.getParent() is not None:
                parentMsgKeys = topicObj.getParent().getArgDescriptions().keys()
            argsDocs = topicObj.getArgDescriptions()
            for key, argDesc in argsDocs.iteritems():
                if key not in parentMsgKeys:
                    msg = "- %s: %s" % (key, argDesc)
                    self.__formatItem(msg, extraIndent)
            self.__formatItem("'''", extraIndent)

    def __formatItem(self, item, extraIndent=0):
        indent = extraIndent + self.__indent
        indentStr = self.INDENT_CH * indent
        lines = item.splitlines()
        for line in lines:
            self.__output.append( '%s%s' % (indentStr, line) )

    def __formatBlock(self, text, extraIndent=0):
        self.__wrapper.initial_indent = self.INDENT_CH * (self.__indent + extraIndent)
        self.__wrapper.subsequent_indent = self.__wrapper.initial_indent
        self.__output.append( self.__wrapper.fill(text) )


