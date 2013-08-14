'''
Pubsub provides components required to support publish-subscribe
messaging within an application. The publish-subscribe package provides the
following modules:

- ``pub``: first and foremost, provides functions for sending messages
  and subscribing listeners. It also provides functions and base classes for
  improving robustness of pubsub-based applications: tracking pubsub usage,
  handling exceptions in listeners, and specificying message topic
  hierarchy, to name a few.
- ``utils``: subpackage of utility functions and classes, some based on
  base classe defined in pub core. They provide
  basic pubsub usage tracker, exception handler, topic tree printer,
  and more. These can also serve as examples of how to create your
  own trackers/handlers/etc.

Two modules allow to choose the messaging protocol
and must be used only ONCE in an application:

- ``setupkwargs``: setup pubsub to use "kwargs" messaging protocol
  This is the default so it is not usually necessary to use setupkwargs.
- ``setuparg1``: setup pubsub to use "arg1" messaging protocol.

Typical usage would be

> from pubsub import pub
> def myListener(greeting, name):
>   print greeting.capitalize(), name.capitalize()
> pub.subscribe(myListener, 'your.topic')
> pub.sendMessage('your.topic', greeting='hello', name='you')
> Hello You

The source distribution has many more examples.
'''

'''
:copyright: Copyright 2013 by Oliver Schoenborn, all rights reserved.
:license: BSD, see LICENSE.txt for details.

Last change info:
- $Date: 2013-05-21 01:38:06 +0000 (Tue, 21 May 2013) $
- $Revision: 290 $

'''


__all__ = [
    'pub',
    'utils',
    'setupkwargs',
    'setuparg1',
    ]


