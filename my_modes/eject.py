from procgame.game import AdvancedMode

class CoilEjectMode(AdvancedMode):
    # Eject any balls that get stuck before returning to the trough.

    def mode_started(self):
        # eject balls that are already stuck when the mode started
        delay = 0
        for sw in ['popperL', 'popperR', 'shooterL', 'shooterR']:
            if self.game.switches[sw].is_active():
                self.delay(name='pulse_coil', event_type=None, delay=delay, handler=self.pop_coil, param=sw)
                delay += 0.125

    def pop_coil(self, coil):
        self.game.coils[coil].pulse()

    def sw_popperL_active_for_300ms(self, sw):
        self.game.coils.popperL.pulse()

    def sw_popperR_active_for_300ms(self, sw):
        self.game.coils.popperR.pulse()

    def sw_shooterL_active_for_300ms(self, sw):
        self.game.coils.shooterL.pulse()

    def sw_shooterR_active_for_300ms(self, sw):
        self.game.coils.shooterR.pulse()
