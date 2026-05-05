class SessionMixin:
    def _do_get_song_scale(self, args):
        (client,) = args
        try:
            is_active = getattr(self.song(), "scale_mode", 0) == 1
            root_note = getattr(self.song(), "root_note", -1)
            scale_name = getattr(self.song(), "scale_name", "Unknown")
            self._send_response(
                client,
                {
                    "is_active": is_active,
                    "root_note": root_note,
                    "scale_name": scale_name,
                },
            )
        except Exception as e:
            self._send_error(client, str(e))

    def _do_get_session_info(self, client):
        try:
            tracks_info = []
            for i, track in enumerate(self.song().tracks):
                vol = "UNKNOWN"
                pan = "UNKNOWN"
                try:
                    vol = track.mixer_device.volume.value
                    pan = track.mixer_device.panning.value
                except Exception:
                    pass

                track_type = (
                    "midi" if getattr(track, "has_midi_input", False) else "audio"
                )
                devices = [str(d.name) for d in getattr(track, "devices", [])]

                clips = {}
                try:
                    for j, slot in enumerate(track.clip_slots):
                        if slot.has_clip and getattr(slot, "clip", None):
                            clips[str(j)] = str(slot.clip.name)
                except Exception:
                    pass

                tracks_info.append(
                    {
                        "index": i,
                        "name": track.name,
                        "type": track_type,
                        "volume": vol,
                        "panning": pan,
                        "devices": devices,
                        "clips": clips,
                    }
                )

            returns_info = []
            for i, track in enumerate(self.song().return_tracks):
                vol = "UNKNOWN"
                pan = "UNKNOWN"
                try:
                    vol = track.mixer_device.volume.value
                    pan = track.mixer_device.panning.value
                except Exception:
                    pass

                devices = [str(d.name) for d in getattr(track, "devices", [])]

                returns_info.append(
                    {
                        "index": i,
                        "name": track.name,
                        "volume": vol,
                        "panning": pan,
                        "devices": devices,
                    }
                )

            master_info = {}
            try:
                master = self.song().master_track
                vol = "UNKNOWN"
                pan = "UNKNOWN"
                try:
                    vol = master.mixer_device.volume.value
                    pan = master.mixer_device.panning.value
                except Exception:
                    pass

                devices = [str(d.name) for d in getattr(master, "devices", [])]

                master_info = {"volume": vol, "panning": pan, "devices": devices}
            except Exception:
                pass

            info = {
                "tempo": self.song().tempo,
                "is_playing": self.song().is_playing,
                "root_note": getattr(self.song(), "root_note", -1),
                "scale_name": getattr(self.song(), "scale_name", "Unknown"),
                "tracks": tracks_info,
                "returns": returns_info,
                "master": master_info,
            }
            self._send_response(client, info, apply_toon=False)
        except Exception as e:
            self.log_message(f"Get session info err: {e}")
            self._send_error(client, str(e))

    def _do_set_tempo(self, tempo):
        try:
            self.song().tempo = tempo
            self.log_message(f"Set tempo to {tempo}")
        except Exception as e:
            self.log_message(str(e))

    def _do_start_playback(self):
        self.song().is_playing = True

    def _do_stop_playback(self):
        self.song().is_playing = False
