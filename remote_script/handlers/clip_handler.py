import Live

class ClipMixin:
    def _do_create_clip(self, params):
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)
            length = params.get("length", 4.0)
            clip_name = params.get("clip_name", "")
            slot = self.song().tracks[t_idx].clip_slots[c_idx]
            if not slot.has_clip:
                slot.create_clip(length)
                if clip_name and slot.clip:
                    slot.clip.name = clip_name
        except Exception as e:
            self.log_message(f"Create clip err: {e}")

    def _do_fire_clip(self, params):
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)
            self.song().tracks[t_idx].clip_slots[c_idx].fire()
        except Exception as e:
            self.log_message(f"Fire clip err: {e}")

    def _do_set_clip_name(self, params):
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)
            name = params.get("name", "New Clip")
            clip = self.song().tracks[t_idx].clip_slots[c_idx].clip
            if clip:
                clip.name = name
        except Exception as e:
            self.log_message(f"Set clip name err: {e}")

    def _do_stop_clip(self, params):
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)
            self.song().tracks[t_idx].clip_slots[c_idx].stop()
        except Exception as e:
            self.log_message(f"Stop clip err: {e}")

    def _do_add_notes(self, params):
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)
            notes_req = params.get("notes", [])

            clip = self.song().tracks[t_idx].clip_slots[c_idx].clip
            if not clip:
                return

            notes_to_add = tuple(
                Live.Clip.MidiNoteSpecification(
                    pitch=n["pitch"],
                    start_time=n["start_time"],
                    duration=n["duration"],
                    velocity=n["velocity"],
                    mute=False,
                )
                for n in notes_req
            )
            clip.add_new_notes(notes_to_add)
        except Exception as e:
            self.log_message(f"Add notes err: {e}")

    def _do_inject_midi_to_new_clip(self, args):
        params, client = args
        try:
            t_idx = params.get("track_index", 0)
            length = params.get("length", 4.0)
            notes_req = params.get("notes", [])
            clip_name = params.get("clip_name", "")

            if t_idx >= len(self.song().tracks):
                self._send_error(client, "Track index out of bounds")
                return

            track = self.song().tracks[t_idx]

            open_slot_idx = -1
            for i, slot in enumerate(track.clip_slots):
                if not slot.has_clip:
                    open_slot_idx = i
                    break

            if open_slot_idx == -1:
                self._send_error(client, "No empty clip slots available on the track.")
                return

            slot = track.clip_slots[open_slot_idx]
            slot.create_clip(length)
            clip = slot.clip

            if clip_name and clip:
                clip.name = clip_name

            if notes_req and clip:
                notes_to_add = tuple(
                    Live.Clip.MidiNoteSpecification(
                        pitch=n["pitch"],
                        start_time=n["start_time"],
                        duration=n["duration"],
                        velocity=n["velocity"],
                        mute=False,
                    )
                    for n in notes_req
                )
                clip.add_new_notes(notes_to_add)

            self._send_response(
                client, {"status": "success", "clip_slot_index": open_slot_idx}
            )
        except Exception as e:
            self._send_error(client, f"Inject midi err: {e}")

    def _do_get_notes_from_clip(self, args):
        params, client = args
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)

            if t_idx >= len(self.song().tracks):
                self._send_error(client, "Track index out of bounds")
                return
            track = self.song().tracks[t_idx]
            if c_idx >= len(track.clip_slots):
                self._send_error(client, "Clip slot index out of bounds")
                return
            clip = track.clip_slots[c_idx].clip
            if not clip:
                self._send_response(client, [])
                return

            out_notes = []
            if clip:
                notes = clip.get_notes_extended(
                    int(0), int(128), float(0.0), float(9999.0)
                )
                for n in notes:
                    out_notes.append(
                        {
                            "pitch": n.pitch,
                            "start_time": n.start_time,
                            "duration": n.duration,
                            "velocity": n.velocity,
                        }
                    )
            self._send_response(client, out_notes)
        except Exception as e:
            self._send_error(client, f"Get notes err: {e}")

    def _do_delete_notes_from_clip(self, params):
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)
            notes_req = params.get("notes", [])

            if t_idx >= len(self.song().tracks):
                return
            track = self.song().tracks[t_idx]
            if c_idx >= len(track.clip_slots):
                return
            clip = track.clip_slots[c_idx].clip
            if not clip:
                return

            for n in notes_req:
                pitch = n.get("pitch")
                start_time = n.get("start_time")
                if pitch is not None and start_time is not None:
                    clip.remove_notes_extended(
                        int(pitch), int(1), float(start_time), float(0.01)
                    )
        except Exception as e:
            self.log_message(f"Delete notes err: {e}")

    def _do_delete_clip(self, params):
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)
            if t_idx >= len(self.song().tracks):
                return
            track = self.song().tracks[t_idx]
            if c_idx >= len(track.clip_slots):
                return
            track.clip_slots[c_idx].delete_clip()
        except Exception as e:
            self.log_message(f"Delete clip err: {e}")
