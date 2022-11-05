from procgame.game import AdvancedMode

class StallSearch(AdvancedMode):
    '''Eject non-captive balls that get stuck in shooter lanes and VUKs.
       The game declares it is keeping balls captive intentionally by calling mark_captive(sw).
       The game declares it ejected a captive ball by calling mark_captive(sw, is_captive=False)
       We want to repeatedly try to eject a ball that got stuck because the coil did not fire,
       (probably because the coin door was open).'''

    def __init__(self, game, priority):
        super(StallSearch, self).__init__(game, priority, AdvancedMode.System)
        self.period = 2

    def mode_started(self):
        self.restart()

    def restart(self):
        '''mark all shooter lane and VUK switches as non-captive and check for stuck balls right away'''
        self.captive = {'shooterL':False, 'shooterR': False, 'popperL': False, 'popperR': False}
        self.check_now()

    def check_now(self):
        self.cancel_delayed('check_captive')
        self.check_captive()

    def check_captive(self):
        # give time for the game to react if the player is playing
        seconds = 2 if self.game.base_play.is_started() else None
        delay = 0
        for sw in self.captive:
            if not self.captive[sw] and self.game.switches[sw].is_active(seconds):
                self.delay(name='pop_coil', event_type=None, delay=delay, handler=self.pop_coil, param=sw)
                delay += 0.125
        self.delay(name='check_captive', event_type=None, delay=max(delay, self.period), handler=self.check_captive)

    def mark_captive(self, sw, is_captive=True):
        self.captive[sw] = is_captive
        if not is_captive:
            # the game just pulsed the coil, give the ball some time to eject before we check
            self.cancel_delayed('check_captive')
            self.delay(name='check_captive', event_type=None, delay=self.period, handler=self.check_captive)

    def pop_coil(self, coil):
        # no point in pulsing the coil and hear the faint attempt if the coin door is still opened
        if self.game.switches[coil].is_active() and self.game.switches.coinDoor.is_active():
            self.game.coils[coil].pulse()

    def sw_popperL_active_for_300ms(self, sw):
        self.check_now()

    def sw_popperR_active_for_300ms(self, sw):
        self.check_now()

    def sw_shooterL_active_for_300ms(self, sw):
        self.check_now()

    def sw_shooterR_active_for_300ms(self, sw):
        self.check_now()
