import re

class DeviceMixin:
    def _do_get_track_devices(self, args):
        params, client = args
        try:
            t_idx = int(params.get("track_index", 0))
            track = self.song().tracks[t_idx]

            out_devices = []
            for i, d in enumerate(track.devices):
                out_devices.append({"index": i, "name": str(d.name)})
            self._send_response(client, out_devices)
        except IndexError:
            self._send_error(
                client,
                f"Track index {params.get('track_index', 0)} out of bounds. Tracks are 0-indexed.",
            )
        except Exception as e:
            self._send_error(client, f"Get track devices err: {str(e)}")

    def _do_get_device_parameters(self, args):
        params, client = args
        try:
            t_idx = int(params.get("track_index", 0))
            d_idx = int(params.get("device_index", 0))

            track = self.song().tracks[t_idx]
            device = track.devices[d_idx]

            out_params = []
            for i, p in enumerate(device.parameters):
                out_params.append(
                    {
                        "index": i,
                        "name": str(p.name),
                        "value": float(p.value),
                        "display_value": str(p),
                        "min": float(p.min),
                        "max": float(p.max),
                    }
                )
            self._send_response(
                client, {"device_name": str(device.name), "parameters": out_params}
            )
        except IndexError:
            self._send_error(
                client,
                f"Track or Device index out of bounds. t_idx={params.get('track_index')} d_idx={params.get('device_index')}",
            )
        except Exception as e:
            self._send_error(client, f"Get device params err: {str(e)}")

    def _do_set_device_parameter(self, args):
        params, client = args
        try:
            t_idx = int(params.get("track_index", 0))
            d_idx = int(params.get("device_index", 0))
            p_name = params.get("parameter_name", "")
            val = params.get("value", 0.0)

            track = self.song().tracks[t_idx]
            device = track.devices[d_idx]

            target_name = re.sub(r"[^a-z0-9]", "", str(p_name).lower())
            if not target_name:
                self._send_error(client, "Parameter name cannot be empty")
                return

            best_match = None

            # 1. Exact match (case-insensitive, fully alphanumeric)
            exact_matches = [
                p
                for p in device.parameters
                if re.sub(r"[^a-z0-9]", "", str(p.name).lower()) == target_name
            ]
            if len(exact_matches) == 1:
                best_match = exact_matches[0]
            elif len(exact_matches) > 1:
                names = [str(p.name) for p in exact_matches]
                self._send_error(
                    client,
                    f"Ambiguous parameter name. Multiple matches found: {names}. Please provide the exact parameter name.",
                )
                return

            # 2. Substring match
            if not best_match:
                sub_matches = []
                for p in device.parameters:
                    p_norm = re.sub(r"[^a-z0-9]", "", str(p.name).lower())
                    if target_name in p_norm or p_norm in target_name:
                        sub_matches.append(p)

                if len(sub_matches) == 1:
                    best_match = sub_matches[0]
                elif len(sub_matches) > 1:
                    names = [str(p.name) for p in sub_matches]
                    self._send_error(
                        client,
                        f"Ambiguous parameter name. Multiple matches found: {names}. Please provide the exact parameter name.",
                    )
                    return

            # 3. Synonym mapping
            if not best_match:
                synonyms = {
                    "cutoff": ["freq", "filterfreq"],
                    "freq": ["cutoff"],
                    "volume": ["gain", "out", "level"],
                    "gain": ["volume", "level"],
                    "level": ["volume", "gain"],
                }

                mapped_targets = synonyms.get(target_name, [])
                syn_matches = []
                for p in device.parameters:
                    p_norm = re.sub(r"[^a-z0-9]", "", str(p.name).lower())
                    for syn in mapped_targets:
                        if syn == p_norm or syn in p_norm or p_norm in syn:
                            if p not in syn_matches:
                                syn_matches.append(p)

                if len(syn_matches) == 1:
                    best_match = syn_matches[0]
                elif len(syn_matches) > 1:
                    names = [str(p.name) for p in syn_matches]
                    self._send_error(
                        client,
                        f"Ambiguous parameter name. Multiple matches found: {names}. Please provide the exact parameter name.",
                    )
                    return

            if not best_match:
                self._send_error(
                    client, f"Parameter '{p_name}' not found on device '{device.name}'."
                )
                return

            # Safety clamp and assign
            clampped_val = max(
                float(best_match.min), min(float(best_match.max), float(val))
            )
            best_match.value = clampped_val
            self._send_response(client, str(best_match))
        except IndexError:
            self._send_error(
                client,
                f"Track or Device index out of bounds. t_idx={params.get('track_index')} d_idx={params.get('device_index')}",
            )
        except Exception as e:
            self.log_message(f"Set device param err: {str(e)}")
            self._send_error(client, f"Set device param err: {str(e)}")
