extends SceneTree
## Read/decode only. Never encodes images, edits source or writes runtime cache.

var configuration: Dictionary = {}
var results: Array[Dictionary] = []
var started: int

func _initialize() -> void:
	started = Time.get_ticks_msec()
	var args := OS.get_cmdline_user_args()
	if args.size() != 1:
		push_error("Expected one private decode-only configuration")
		quit(2)
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	if not parsed is Dictionary:
		push_error("Invalid private decode-only configuration")
		quit(2)
		return
	configuration = parsed
	_run.call_deferred()

func _sha(data: PackedByteArray) -> String:
	var hash := HashingContext.new()
	hash.start(HashingContext.HASH_SHA256)
	hash.update(data)
	return hash.finish().hex_encode()

func _write(status: String, reason: String = "") -> void:
	var output := FileAccess.open(String(configuration.result_path),FileAccess.WRITE)
	if output == null:
		push_error("Cannot write private decode-only report")
		return
	output.store_string(JSON.stringify({"status":status,"error":reason,"engine":Engine.get_version_info(),
		"runtime_project_sha256":_sha(FileAccess.get_file_as_bytes(String(configuration.runtime_project_file))),
		"cases":results,"elapsed_seconds":float(Time.get_ticks_msec()-started)/1000.0,
		"scope":"Read-only actual newly imported CTEX vs frozen old CTEX, completeRGBA including transparentRGB; no encoding, runtime mutation, export or visual approval."},"\t")+"\n")
	output.close()

func _fail(reason: String) -> void:
	push_error(reason)
	_write("failed",reason)
	quit(2)

func _parse(data: PackedByteArray) -> Dictionary:
	if data.size() < 52 or data.slice(0,4).get_string_from_ascii() != "GST2" or data.decode_u32(36) != 2:
		return {"error":"Expected GST2/WebP texture"}
	var packets: Array[PackedByteArray] = []
	var position: int = 52
	var count: int = int(data.decode_u32(44))+1
	if count < 1 or count > 32:
		return {"error":"Invalid texture mip count"}
	for level in range(count):
		if position+4 > data.size():
			return {"error":"Missing mip length"}
		var length: int = int(data.decode_u32(position))
		position += 4
		if length <= 0 or length > data.size()-position:
			return {"error":"Mip exceeds texture bounds"}
		packets.append(data.slice(position,position+length))
		position += length
	if position != data.size():
		return {"error":"Unexpected trailing texture bytes"}
	return {"packets":packets,"header":data.slice(0,52)}

func _run() -> void:
	if FileAccess.file_exists(String(configuration.result_path)):
		push_error("Refusing to replace a completed decode-only report")
		quit(2)
		return
	var runtime_config := ConfigFile.new()
	if runtime_config.load(String(configuration.runtime_project_file)) != OK:
		_fail("Cannot read actual runtime project settings")
		return
	if int(runtime_config.get_value("rendering","textures/webp_compression/compression_method",2)) != 6 or float(runtime_config.get_value("rendering","textures/webp_compression/lossless_compression_factor",25)) != 100.0:
		_fail("Actual runtime project does not pin candidate method6/factor100")
		return
	if configuration.cases.size() != int(configuration.expected_cases):
		_fail("Unexpected decode-only case count")
		return
	for sample: Dictionary in configuration.cases:
		var before := FileAccess.get_file_as_bytes(String(sample.before))
		var after := FileAccess.get_file_as_bytes(String(sample.after))
		if _sha(before) != String(sample.before_sha256):
			_fail("Frozen old texture SHA mismatch")
			return
		var a := _parse(before)
		var b := _parse(after)
		if a.has("error") or b.has("error"):
			_fail("Invalid before/after texture: "+String(sample.name))
			return
		if a.header != b.header or a.packets.size() != b.packets.size() or a.packets.size() != int(sample.expected_total_mip_levels):
			_fail("Texture header/mip count changed: "+String(sample.name))
			return
		var mips: Array[Dictionary] = []
		for level in range(a.packets.size()):
			var old_image := Image.new()
			var new_image := Image.new()
			if old_image.load_webp_from_buffer(a.packets[level]) != OK or new_image.load_webp_from_buffer(b.packets[level]) != OK:
				_fail("Godot cannot decode before/after mip")
				return
			var size_equal := old_image.get_size() == new_image.get_size()
			var format_equal := old_image.get_format() == new_image.get_format()
			var dimensions := old_image.get_size()
			var format := old_image.get_format()
			old_image.convert(Image.FORMAT_RGBA8)
			new_image.convert(Image.FORMAT_RGBA8)
			var pixels_before := old_image.get_data()
			var pixels_after := new_image.get_data()
			var rgba_equal := pixels_before == pixels_after
			mips.append({"level":level,"dimensions":[dimensions.x,dimensions.y],"decoded_format":format,
				"dimensions_exact":size_equal,"decoded_format_exact":format_equal,
				"complete_RGBA_bytes_exact_including_transparent_RGB":rgba_equal,
				"before_RGBA_sha256":_sha(pixels_before),"after_RGBA_sha256":_sha(pixels_after)})
			if not size_equal or not format_equal or not rgba_equal:
				results.append({"name":sample.name,"mips":mips,"passed":false})
				_fail("Actual imported mip pixel/dimension/format mismatch: "+String(sample.name))
				return
		results.append({"name":sample.name,"source":sample.source,"before_sha256":_sha(before),"after_sha256":_sha(after),
			"before_bytes":before.size(),"after_bytes":after.size(),"saved_bytes":before.size()-after.size(),
			"first52_header_bytes_exact":true,"mip_levels":mips.size(),"passed":true,"mips":mips})
		_write("running")
		print("CTEX_DECODE_ONLY_PASS ",sample.name," mips=",mips.size()," old=",before.size()," new=",after.size())
	_write("complete_all_actual_imported_mips_RGBA_exact")
	print("CTEX_DECODE_ONLY_COMPLETE cases=",results.size())
	quit(0)
