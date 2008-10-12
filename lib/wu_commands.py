from twisted.words.xish import domish

all_commands=[]

def __register(cls):
    all_commands.append(cls())

class BaseCommand(object):
    """Base class for command processors."""

    def __init__(self, name, help=None, extended_help=None):
        self.name=name
        self.help=help
        self.extended_help=extended_help

    def __call__(self, user, prot, args):
        raise NotImplementedError()

class StatusCommand(BaseCommand):

    def __init__(self):
        super(StatusCommand, self).__init__('status', 'Check your status.')

    def __call__(self, user, prot, args):
        prot.send_plain(user.jid, "You're OK by me.")

__register(StatusCommand)