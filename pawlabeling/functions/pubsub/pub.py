'''
This is the main entry-point to pubsub's core functionality. The pub module 
supports:

* messaging: publishing and receiving messages of a given topic
* tracking: tracking certain pubsub calls in an application
* trapping exceptions: dealing with "badly behaved" listeners (ie that leak exceptions)
* specifying topics: defining (or just documenting) the topic tree of an 
  application; pubsub will verify that your senders and listeners adhere to
  to it

The ``pub`` module also exposes several
classes such as Topic, Listener, Publisher, and many more that could
be used in advanced pub-sub applications.

Note that many functions in this module actually make use of an 
instance of Publisher and one of TopicManager, both created upon import.

About topic definition tree:

Using ``pub.sendMessage('your.topic.name', **kwargs)`` is nice but in bigger
apps you soon realize that two types of issues can make debugging painful: 

1. typos are too easy, yet will create new topics, 
	causing your messages to never reach one or more (even all) of your 
	listeners. 
2. By default, pubsub infers from the first sendMessage or subscribe (whichever
	is execute first during a run) what the message arguments are. Thereafter, 
	all other calls to sendMessage and subscribe must adhere to the same kwarg 
	names. A typo in the arg name will cause an en exception to get thrown, 
	although the fault may in fact be in the first sender or subscription for
	the topic used. 

To help with #2, it is possible to create a hierarchy of topic definitions,
which contain the topic names and a signature that all listeners of the
topic will have to satisfy. To help with #1, setTopicUnspecfiedFatal() can be 
called after pubsub has been imported, then only topics that have a definition 
are allowed; typos will cause an exception. 

The format of this tree can be seen by calling
exportTopicTreeSpec(moduleName='yourModule'); then look at the contents of the
yourModule.py. 

A typical workflow would be:

- use exportTopicTreeSpec() once in a while and inspect the generated
  file for topics that differ only by a typo, fix issues
- once the topic tree has started to gel, save the topic tree file
  created by exportTopicTreeSpec() and complete it with documentation
- use addTopicDefnProvider() and setTopicUnspecifiedFatal()
- to add new topics, manually add them to the topic tree file, OR
  comment out the call to setTopicUnspecifiedFatal() and recall
  exportTopicTreeSpec (your docs should *not* be affected but YMMV)
  
Note that by importing the topic tree file, some editors will provide 
code completion on topic names. Example::

	from pubsub import pub
	import your_topic_tree_module
	pub.addTopicDefnProvider(your_topic_tree_module)
	pub.setTopicUnspecifiedFatal()

	pub.subscribe(listener, your_topic_tree_module.topic1)
	pub.sendMessage(your_topic_tree_module.topic1.subtopic1, kwarg1=..., ...)

  TODO: add isMsgReceivable(listener, topicName) to find out if listener is
        subscribed to topicName or any of its subtopics.

:copyright: Copyright since 2006 by Oliver Schoenborn, all rights reserved.
:license: BSD, see LICENSE.txt for details.

'''

PUBSUB_VERSION = 3                      # DO NOT CHANGE
SVN_VERSION = "$Rev: 243 $".split()[1]  # DO NOT CHANGE
VERSION_STR = "3.2.0b.201112.r" + SVN_VERSION  # update at each new release


from core.listener import (
    Listener,
    getID as getListenerID,
    ListenerInadequate
    )

from core.topicobj import (
    Topic,
    SenderMissingReqdArgs, 
    SenderUnknownOptArgs, 
    ListenerSpecInvalid, 
    ListenerNotValidatable, 
    ExcHandlerError
    )

from core.topicmgr import (
    TopicManager as _TopicManager,
    ListenerSpecIncomplete,
    UndefinedTopic,
    UndefinedSubtopic,
    ALL_TOPICS
    )

from core.topicdefnprovider import (
    ITopicDefnProvider, 
    TopicDefnProvider, 
    registerTypeForImport as registerTopicDefnProviderType,
    TOPIC_TREE_FROM_MODULE,
    TOPIC_TREE_FROM_STRING,
    TOPIC_TREE_FROM_CLASS, 
    exportTopicTreeSpec,
    TopicTreeTraverser
    )

from core.publisher import Publisher


__all__ = [
    # listener stuff:
    'Listener', 
    'ListenerInadequate',
    'isValid', 
    'validate',

    # topic stuff:
    'ALL_TOPICS', 
    'Topic',
    'topics', 
    'topicsMap', 
    'AUTO_TOPIC',
    'getOrCreateTopic', 
    'getTopic', 
    'newTopic', 
    'delTopic',
    'ListenerSpecIncomplete', 
    'ListenerNotValidatable',
    'UndefinedTopic', 
    'UndefinedSubtopic', 
    'ExcHandlerError',
    'getAssociatedTopics',
    'getDefaultTopicMgr', 
    'getDefaultTopicTreeRoot',

    # topioc defn provider stuff
    'addTopicDefnProvider', 
    'clearTopicDefnProviders',
    'registerTopicDefnProviderType', 
    'TOPIC_TREE_FROM_MODULE',
    'TOPIC_TREE_FROM_CLASS', 
    'TOPIC_TREE_FROM_STRING',
    'exportTopicTreeSpec', 
    'TopicTreeTraverser',

    # publisher stuff:
    'Publisher',
    'subscribe', 
    'unsubscribe', 
    'isSubscribed', 
    'unsubAll',
    'sendMessage', 
    'SenderMissingReqdArgs', 
    'SenderUnknownOptArgs',
    'getListenerExcHandler', 
    'setListenerExcHandler',
    'addNotificationHandler', 
    'setNotificationFlags', 
    'clearNotificationHandlers',
    'setTopicUnspecifiedFatal',

    # misc:
    'PUBSUB_VERSION',
    ]


# ---------------------------------------------

_publisher = Publisher()

subscribe   = _publisher.subscribe
unsubscribe = _publisher.unsubscribe
unsubAll    = _publisher.unsubAll
sendMessage = _publisher.sendMessage

getListenerExcHandler     = _publisher.getListenerExcHandler
setListenerExcHandler     = _publisher.setListenerExcHandler
addNotificationHandler    = _publisher.addNotificationHandler
clearNotificationHandlers = _publisher.clearNotificationHandlers
setNotificationFlags      = _publisher.setNotificationFlags
getNotificationFlags      = _publisher.getNotificationFlags

setTopicUnspecifiedFatal = _publisher.setTopicUnspecifiedFatal
getMsgProtocol = _publisher.getMsgProtocol


def getDefaultPublisher():
    '''Get the Publisher that is created by default when you
    import package.'''
    return _publisher


# ---------------------------------------------
_topicMgr = _publisher.getTopicMgr()

topics    = _topicMgr.getRootTopic()
topicsMap = _topicMgr._topicsMap
AUTO_TOPIC  = Listener.AUTO_TOPIC


def isValid(listener, topicName):
    '''Return true only if listener can subscribe to messages of
    type topicName.'''
    return _topicMgr.getTopic(topicName).isValid(listener)


def validate(listener, topicName):
    '''Checks if listener can subscribe to topicName. If not, raises
    ListenerInadequate, otherwise just returns.'''
    _topicMgr.getTopic(topicName).validate(listener)


def isSubscribed(listener, topicName):
    '''Returns true if listener has subscribed to topicName, false otherwise.
    WARNING: a false return is not a guarantee that listener won't get
    messages of topicName: it could receive messages of a subtopic of
    topicName. '''
    return _topicMgr.getTopic(topicName).hasListener(listener)


def getDefaultTopicMgr():
    '''Get the topic manager that is created by default when you
    import package.'''
    return _topicMgr

def getDefaultTopicTreeRoot():
    '''Get the topic that is parent of all root (ie top-level) topics. Useful
    characteristics:

    - "root of all topics" topic satisfies isAll()==True, isRoot()==False,
      getParent() is None;
    - all top-level topics satisfy isAll()==False, isRoot()==True, and
      getParent() is getDefaultTopicTreeRoot();
    - all other topics satisfy neither. '''
    return _topicMgr.getRootTopic()

getOrCreateTopic     = _topicMgr.getOrCreateTopic
newTopic             = _topicMgr.newTopic
delTopic             = _topicMgr.delTopic
getTopic             = _topicMgr.getTopic
getAssociatedTopics  = _topicMgr.getTopics


addTopicDefnProvider     = _topicMgr.addDefnProvider
clearTopicDefnProviders  = _topicMgr.clearDefnProviders
getNumTopicDefnProviders = _topicMgr.getNumDefnProviders

def instantiateAllDefinedTopics(provider):
    '''Topics are normally "instantiated" on demand, even if definition 
    providers are registered. This function is a utility to loop over 
    all topics of given provider and instantiate each one. Useful mainly 
    for testing.'''
    for topicName in provider:
        getOrCreateTopic(topicName)
        
#---------------------------------------------------------------------------
