class TrackMixin:
    def _do_create_midi_track(self, track_name):
        try:
            self.song().create_midi_track(-1)
            new_track = self.song().tracks[-1]
            new_track.name = track_name
            self.log_message(f"Created MIDI track: {track_name}")
        except Exception as e:
            self.log_message(f"Error creating track: {e}")

    def _do_set_track_name(self, args):
        idx, name = args
        try:
            self.song().tracks[idx].name = name
        except Exception as e:
            self.log_message(f"Error setting track name: {e}")

    def _do_select_track(self, track_name):
        for track in self.song().tracks:
            if track.name == track_name:
                self.song().view.selected_track = track
                return

    def _do_arm_track(self, args):
        track_name, arm = args
        for track in self.song().tracks:
            if track.name == track_name and track.can_be_armed:
                track.arm = arm

    def _do_delete_track(self, params):
        try:
            t_idx = params.get("track_index", 0)
            if t_idx >= 0 and t_idx < len(self.song().tracks):
                self.song().delete_track(t_idx)
            else:
                self.log_message(f"Delete track err: Invalid index {t_idx}")
        except Exception as e:
            self.log_message(f"Delete track err: {e}")

    def _do_set_track_mixer(self, args):
        params, client = args
        try:
            t_idx = params.get("track_index")
            if t_idx is None:
                self._send_error(client, "track_index is required")
                return
            t_idx = int(t_idx)

            if t_idx < 0 or t_idx >= len(self.song().tracks):
                self._send_error(client, f"Track index {t_idx} out of bounds")
                return

            track = self.song().tracks[t_idx]

            if "volume" in params:
                try:
                    vol = float(params["volume"])
                    track.mixer_device.volume.value = max(0.0, min(1.0, vol))
                except Exception as e:
                    self.log_message(f"Error setting volume: {e}")

            if "panning" in params:
                try:
                    pan = float(params["panning"])
                    track.mixer_device.panning.value = max(-1.0, min(1.0, pan))
                except Exception as e:
                    self.log_message(f"Error setting panning: {e}")

            if "mute" in params:
                try:
                    mute_val = bool(params["mute"])
                    track.mute = mute_val
                except Exception as e:
                    self.log_message(f"Error setting mute: {e}")

            self._send_response(client, "ok")
        except Exception as e:
            self.log_message(f"Set track mixer err: {str(e)}")
            self._send_error(client, f"Set track mixer err: {str(e)}")
