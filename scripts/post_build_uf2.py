Import("env")
import os


def generate_uf2(source, target, env):
    """Generate UF2 file after hex is built"""
    build_dir = env.subst("$BUILD_DIR")
    progname = env.subst("${PROGNAME}")
    firmware_hex = os.path.join(build_dir, progname + ".hex")
    firmware_uf2 = os.path.join(build_dir, progname + ".uf2")

    # UF2 family ID for nRF52840
    family_id = "0xADA52840"

    # Path to uf2conv.py
    uf2conv_path = os.path.join(env.get("PROJECT_DIR"), "scripts", "uf2conv.py")

    if os.path.exists(uf2conv_path) and os.path.exists(firmware_hex):
        env.Execute(
            f'python3 "{uf2conv_path}" -f {family_id} -c -o "{firmware_uf2}" "{firmware_hex}"'
        )
        print(f"Generated UF2: {firmware_uf2}")
    else:
        if not os.path.exists(firmware_hex):
            print(f"Warning: hex file not found: {firmware_hex}")
        if not os.path.exists(uf2conv_path):
            print(f"Warning: uf2conv.py not found at {uf2conv_path}")


# Hook after the hex file is built
env.AddPostAction("$BUILD_DIR/${PROGNAME}.hex", generate_uf2)
