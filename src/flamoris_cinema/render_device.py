"""Explicit Cycles device selection; no runtime/service or persistent prefs changes."""


def validate_options(backend, gpu_name, threads):
    if backend not in ('CPU', 'HIP'):
        raise ValueError('device must be CPU or HIP')
    if type(threads) is not int or not 1 <= threads <= 64:
        raise ValueError('threads must be integer in 1..64')
    if gpu_name is not None:
        if backend != 'HIP' or not isinstance(gpu_name, str) or not gpu_name.strip() or len(gpu_name) > 200:
            raise ValueError('gpu-name requires HIP and a nonempty name/id fragment')


def choose_hip_device(devices, gpu_name=None):
    candidates = [d for d in devices if d.get('type') == 'HIP']
    if gpu_name is not None:
        query = gpu_name.casefold()
        candidates = [d for d in candidates if query in d['name'].casefold() or query in d['id'].casefold()]
    if not candidates:
        raise ValueError('no matching HIP GPU found; CPU fallback is disabled')
    if len(candidates) != 1:
        raise ValueError('multiple HIP GPUs match; specify a unique --gpu-name name/id fragment')
    return candidates[0]


def configure_cycles(scene, backend='CPU', gpu_name=None, threads=2):
    """Configure the current process. This reports selection, not GPU telemetry."""
    import bpy
    validate_options(backend, gpu_name, threads)
    scene.render.threads_mode, scene.render.threads = 'FIXED', threads
    report = {'backend': backend, 'cycles_device': 'CPU', 'threads': threads,
              'devices': [], 'cpu_render_enabled': True, 'hiprt': False}
    if backend == 'CPU':
        scene.cycles.device = 'CPU'
        return report
    addon = bpy.context.preferences.addons.get('cycles')
    if addon is None:
        raise ValueError('Cycles preferences unavailable; cannot select HIP')
    preferences = addon.preferences
    try:
        preferences.compute_device_type = 'HIP'
        preferences.refresh_devices()
    except (TypeError, RuntimeError, AttributeError) as exc:
        raise ValueError('HIP device discovery failed; CPU fallback is disabled') from exc
    inventory = [{'name': d.name, 'id': d.id, 'type': d.type} for d in preferences.devices]
    selected = choose_hip_device(inventory, gpu_name)
    for device in preferences.devices:
        device.use = device.type == 'HIP' and device.id == selected['id']
    scene.cycles.device = 'GPU'
    report.update(cycles_device='GPU', devices=[selected], cpu_render_enabled=False,
                  hiprt=bool(getattr(preferences, 'use_hiprt', False)))
    verify_selection(scene, report)
    print(f"Cinema selected HIP GPU: {selected['name']} (CPU render device disabled)", flush=True)
    return report


def verify_selection(scene, report):
    import bpy
    if scene.cycles.device != report['cycles_device']:
        raise ValueError('Cycles device differs from requested selection')
    if report['backend'] == 'HIP':
        devices = bpy.context.preferences.addons['cycles'].preferences.devices
        enabled = [{'id': d.id, 'type': d.type} for d in devices if d.use]
        expected = [{'id': d['id'], 'type': 'HIP'} for d in report['devices']]
        if enabled != expected:
            raise ValueError('HIP selection changed or CPU render device enabled')
