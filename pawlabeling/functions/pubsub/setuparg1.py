'''
Setup pubsub for use of *arg1* messaging protocol. Without this 
module, the default is the more powerful *kwargs* protocol. The 
*arg1* protocol is identical to the legacy messaging protocol from 
first version of pubsub (when it was still part of wxPython) and 
is *deprecated*. This module is therefore *deprecated*. 

Usage: Import this file before the first 'from pubsub import pub' 
statement to make pubsub use the *arg1* messaging protocol::

    from pubsub import setuparg1
    from pubsub import pub

Note that once :mod:pub has been imported, the messaging protocol
must NOT be changed. 

If you want to migrate an application from 'arg1' to 'kwargs'
style messaging, this module provides a function, 
:func:enforceArgName(), which can help you in this endeavour. 

:copyright: Copyright since 2006 by Oliver Schoenborn, all rights reserved.
:license: BSD, see LICENSE.txt for details.

'''

import core
core.setMsgProtocol('arg1')


def enforceArgName(commonName):
    '''This will configure pubsub to require that all listeners use 
	the same argument name (*commonName*) as first parameter. This could 
	be a ueful first step in transitioning an application that has been 
	using *arg1* protocol to the more powerful *kwargs* protocol. '''
    core.setMsgDataArgName(1, commonName)
