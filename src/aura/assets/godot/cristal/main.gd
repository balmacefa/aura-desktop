extends Node3D
# AuraLive Godot - cristales flotantes interactivos

const N := 44
var state_url := "http://127.0.0.1:8791/state"
var pal: Array[Color] = [Color("0e0e18"), Color("d97757"), Color("1d1b3a"), Color("3a1b2a")]
var cam: Camera3D
var http: HTTPRequest
var env: Environment
var crystals: Array = []   # dictionaries
var cursor := Vector2(0.5, 0.5)
var cursor_w := Vector3(0, 0, 0)
var cpu := 0.2
var last_click := -1
var have_server := false
var since_ok := 999.0
var waves: Array = []      # {o:Vector3, t:float}
var time := 0.0

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--state="):
			state_url = a.substr(8)
		elif a.begins_with("--pal="):
			var parts := a.substr(6).split(",")
			for i in min(4, parts.size()):
				pal[i] = Color.html(parts[i])
	_build_scene()
	http = HTTPRequest.new()
	http.timeout = 1.0
	add_child(http)
	http.request_completed.connect(_on_http)
	var t := Timer.new()
	t.wait_time = 1.0 / 30.0
	t.autostart = true
	t.timeout.connect(_poll)
	add_child(t)

func _poll() -> void:
	if http.get_http_client_status() == HTTPClient.STATUS_DISCONNECTED:
		http.request(state_url)

func _on_http(result: int, code: int, _h: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or code != 200:
		return
	var d = JSON.parse_string(body.get_string_from_utf8())
	if typeof(d) != TYPE_DICTIONARY:
		return
	have_server = true
	since_ok = 0.0
	cursor = Vector2(clampf(float(d.get("x", 0.5)), 0.0, 1.0), clampf(float(d.get("y", 0.5)), 0.0, 1.0))
	cpu = clampf(float(d.get("cpu", 0.2)), 0.0, 1.0)
	var c := int(d.get("click", 0))
	if last_click < 0:
		last_click = c
	elif c != last_click:
		last_click = c
		_spawn_wave()

func _build_scene() -> void:
	env = Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = pal[0]
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = pal[2].lightened(0.2)
	env.ambient_light_energy = 0.6
	env.glow_enabled = true
	env.glow_intensity = 0.9
	env.glow_bloom = 0.15
	env.glow_hdr_threshold = 0.8
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	cam = Camera3D.new()
	cam.fov = 50
	cam.position = Vector3(0, 0, 14)
	add_child(cam)
	var l := DirectionalLight3D.new()
	l.rotation_degrees = Vector3(-35, 30, 0)
	l.light_color = pal[1].lightened(0.3)
	l.light_energy = 0.8
	add_child(l)
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var meshes: Array[Mesh] = []
	for i in 5:
		meshes.append(_make_crystal(rng))
	var cols := [pal[1], pal[1], pal[2].lightened(0.5), pal[3].lightened(0.45), pal[1].lightened(0.3)]
	for i in N:
		var mi := MeshInstance3D.new()
		mi.mesh = meshes[rng.randi() % meshes.size()]
		var m := StandardMaterial3D.new()
		var col: Color = cols[rng.randi() % cols.size()]
		m.albedo_color = Color(col, 0.85)
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.emission_enabled = true
		m.emission = col
		m.emission_energy_multiplier = rng.randf_range(0.6, 1.6)
		m.metallic = 0.3
		m.roughness = 0.35
		mi.material_override = m
		var home := Vector3(rng.randf_range(-11, 11), rng.randf_range(-6, 6), rng.randf_range(-7, 3))
		var s := rng.randf_range(0.35, 1.1)
		mi.scale = Vector3.ONE * s
		mi.position = home
		add_child(mi)
		crystals.append({
			"n": mi, "home": home, "vel": Vector3.ZERO, "s": s, "mat": m,
			"axis": Vector3(rng.randf_range(-1, 1), rng.randf_range(-1, 1), rng.randf_range(-1, 1)).normalized(),
			"spd": rng.randf_range(0.2, 0.7), "ph": rng.randf_range(0, TAU),
			"extra": 0.0, "kick": []
		})

func _make_crystal(rng: RandomNumberGenerator) -> Mesh:
	# bipirámide alargada de lados irregulares (low-poly)
	var sides := rng.randi_range(5, 7)
	var h1 := rng.randf_range(0.9, 1.6)
	var h2 := rng.randf_range(0.5, 1.0)
	var ring: Array[Vector3] = []
	for i in sides:
		var a := TAU * i / sides
		var r := rng.randf_range(0.35, 0.5)
		ring.append(Vector3(cos(a) * r, rng.randf_range(-0.1, 0.1), sin(a) * r))
	var top := Vector3(0, h1, 0)
	var bot := Vector3(0, -h2, 0)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in sides:
		var a := ring[i]
		var b := ring[(i + 1) % sides]
		st.add_vertex(top); st.add_vertex(b); st.add_vertex(a)
		st.add_vertex(bot); st.add_vertex(a); st.add_vertex(b)
	st.generate_normals()
	return st.commit()

func _screen_to_world(p: Vector2) -> Vector3:
	var vs := get_viewport().get_visible_rect().size
	return cam.project_position(Vector2(p.x * vs.x, p.y * vs.y), cam.position.z)

func _spawn_wave() -> void:
	waves.append({"o": cursor_w, "t": 0.0})

func _input(e: InputEvent) -> void:
	if have_server:
		return
	if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
		_spawn_wave()

func _process(dt: float) -> void:
	time += dt
	since_ok += dt
	if since_ok > 1.0:
		have_server = false
	if not have_server:
		var vs := get_viewport().get_visible_rect().size
		var mp := get_viewport().get_mouse_position()
		cursor = Vector2(mp.x / vs.x, mp.y / vs.y)
		cpu = lerpf(cpu, 0.25, dt)
	cursor_w = cursor_w.lerp(_screen_to_world(cursor), clampf(dt * 12.0, 0, 1))
	var speed := 0.6 + cpu * 2.4
	# ondas: cada una se expande y empuja
	for w in waves:
		w.t += dt
	waves = waves.filter(func(w): return w.t < 3.0)
	for c in crystals:
		var n: MeshInstance3D = c.n
		var pos: Vector3 = n.position
		# fuerza de retorno (muelle) + flotación
		var home: Vector3 = c.home + Vector3(0, sin(time * 0.5 * speed + c.ph) * 0.35, 0)
		var f: Vector3 = (home - pos) * 6.0
		# reacción al cursor: repulsión suave
		var d := pos - cursor_w
		d.z = 0
		var dl := d.length()
		c.extra = lerpf(c.extra, 0.0, dt * 2.0)
		if dl < 4.0:
			var k := 1.0 - dl / 4.0
			f += d.normalized() * k * 14.0
			c.extra = maxf(c.extra, k * 3.0)
		# ondas
		for w in waves:
			var wd: Vector3 = pos - w.o
			wd.z = 0
			var r: float = w.t * 14.0
			var diff: float = absf(wd.length() - r)
			if diff < 1.5:
				f += wd.normalized() * (1.0 - diff / 1.5) * 90.0 * (1.0 - w.t / 3.0)
				c.extra = 6.0
		c.vel += f * dt
		c.vel *= maxf(0.0, 1.0 - dt * 2.5)
		n.position = pos + c.vel * dt
		n.rotate(c.axis, (c.spd * speed + c.extra) * dt)
		var m: StandardMaterial3D = c.mat
		m.emission_energy_multiplier = lerpf(m.emission_energy_multiplier, 0.8 + c.extra * 0.4 + cpu * 0.6, dt * 4.0)
