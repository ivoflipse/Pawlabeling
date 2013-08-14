'''
Import this file before the first 'from pubsub import pub' statement
to make pubsub use the *kwargs* messaging protocol::

    from pubsub import setupkwargs
    from pubsub import pub

Note that in an out-of-the-box pubsub installation, this protocol is
the default, so this module should not be necessary. Some pubsub 
installations (such as that in some versions of wxPython) have an 
alternate, 'legacy' API (called *arg1*) as the default, in which 
case this setupkwargs module is useful to configure pubsub for the 
more powerful kwargs protocol. 

Note that once :mod:pub has been imported, the messaging protocol
must NOT be changed. Also, if you are migrating an application from 
'arg1' (legacy) to 'kwargs' style messaging, see :func:transitionFromArg1() 
in this module; it can be useful once you have verified that your 
application runs with the :func:enforceArgName() of setuparg1 module.

:copyright: Copyright since 2006 by Oliver Schoenborn, all rights reserved.
:license: BSD, see LICENSE.txt for details.

'''

import core
core.setMsgProtocol('kwargs')


def transitionFromArg1(commonName):
    '''This will require that all calls to pub.sendMessage() use the
    kwargs protocol, ie named arguments for the message data. This is
    a useful step after setuparg1.enforceArgName(commonName) was used
    and the application debugged. Replace the call to enforceArgName 
	with ::

        setupkwargs.transitionFromArg1(commonName)

    After this stage tested and debugged, this function call
    can be removed, and all reference to the .data attribute of the message
    object received can be removed in all listeners. The migration will 
	then be complete.
    '''
    core.setMsgDataArgName(2, commonName)
