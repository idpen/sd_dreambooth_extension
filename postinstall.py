import filecmp
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig

import git
import requests

from dreambooth import shared


def run(command, desc=None, errdesc=None, custom_env=None, live=True):
    if desc:
        print(desc)

    if live:
        result = subprocess.run(command, shell=True, env=custom_env or os.environ)
        if result.returncode:
            raise RuntimeError(
                f"{errdesc or 'Error running command'}. Command: {command} Error code: {result.returncode}")
        return ""

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True,
                            env=custom_env or os.environ)

    if result.returncode:
        message = f"{errdesc or 'Error running command'}. Command: {command} Error code: {result.returncode}\n"
        message += f"stdout: {result.stdout.decode(encoding='utf8', errors='ignore') or '<empty>'}\n"
        message += f"stderr: {result.stderr.decode(encoding='utf8', errors='ignore') or '<empty>'}\n"
        raise RuntimeError(message)

    return result.stdout.decode(encoding='utf8', errors='ignore')


def actual_install():
    if os.environ.get("PUBLIC_KEY", None):
        print("Docker, returning.")
        shared.launch_error = None
        return
    if sys.version_info < (3, 8):
        import importlib_metadata
    else:
        import importlib.metadata as importlib_metadata

    req_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "requirements.txt")

    # def install_torch(torch_command, use_torch2):
    #     try:
    #         install_cmd = f'"{python}" -m {torch_command}'
    #         print(f"Torch install command: {install_cmd}")
    #         run(install_cmd, f"Installing torch{'2' if use_torch2 else ''} and torchvision.", "Couldn't install torch.")
    #         has_torch = importlib.util.find_spec("torch") is not None
    #         has_torch_vision = importlib.util.find_spec("torchvision") is not None
    #         if use_torch2:
    #             run(f"{python} -m pip install sympy==1.11.1")
    #         torch_installed_ver = str(importlib_metadata.version("torch")) if has_torch else None
    #         torch_vision_check = str(importlib_metadata.version("torchvision")) if has_torch_vision else None
    #         return torch_installed_ver, torch_vision_check
    #     except Exception as e:
    #         print(f"Exception upgrading torch/torchvision: {e}")
    #         return None, None
    #
    # def set_torch2_paths():
    #     # Get the URL for the latest release
    #     url = "https://github.com/ArrowM/xformers/releases/latest"
    #     response = requests.get(url)
    #     resolved_url = response.url
    #     last_portion = resolved_url.split("/")[-1]
    #     d_index = last_portion.index('.d')
    #     revisions = last_portion[d_index + 2:]
    #     revisions = revisions.split("-")
    #     if len(revisions) != 3:
    #         print("Unable to parse revision information.")
    #         return None
    #     torch_version = revisions[0]
    #     python_version = revisions[1]
    #     cuda_version = revisions[2]
    #     xformers_ver = last_portion.replace(f"-{python_version}-{cuda_version}", "")
    #     os_string = "win_amd64" if os.name == "nt" else "linux_x86_64"
    #     torch_ver = f"2.0.0.dev{torch_version}+{cuda_version}"
    #     torch_vis_ver = f"0.15.0.dev{torch_version}+{cuda_version}"
    #     xformers_url = f"{resolved_url}/{xformers_ver}-{python_version}-{python_version}-{os_string}.whl".replace(
    #         "/tag/", "/download/")
    #     torch2_url = f"https://download.pytorch.org/whl/nightly/{cuda_version}/torch-2.0.0.dev{torch_version}%2B{cuda_version}-{python_version}-{python_version}-{os_string}.whl"
    #     torchvision2_url = f"https://download.pytorch.org/whl/nightly/{cuda_version}/torchvision-0.15.0.dev{torch_version}%2B{cuda_version}-{python_version}-{python_version}-{os_string}.whl"
    #     triton_url = f"https://download.pytorch.org/whl/nightly/{cuda_version}/pytorch_triton-2.0.0%2B0d7e753227-{python_version}-{python_version}-linux_x86_64.whl"
    #     xformers_ver = xformers_ver.replace("xformers-", "")
    #     print(f"Xformers version: {xformers_ver}")
    #     print(f"Torch version: {torch_ver}")
    #     print(f"Torch vision version: {torch_vis_ver}")
    #     print(f"xu: {xformers_url}")
    #     print(f"tu: {torch2_url}")
    #     print(f"tvu: {torchvision2_url}")
    #     print(f"tru: {triton_url}")
    #     torch_final = f"{torch2_url} {torchvision2_url}"
    #     if os.name != "nt":
    #         torch_final += f" {triton_url}"
    #     return xformers_ver, torch_ver, torch_vis_ver, xformers_url, torch_final

    def check_versions():
        launch_errors = []
        # use_torch2 = False
        # try:
        #     print(f"ARGS: {sys.argv}")
        #     if "--torch2" in sys.argv:
        #         use_torch2 = True
        #
        #     print(f"Torch2 Selected: {use_torch2}")
        # except:
        #     pass
        #
        # if use_torch2 and not (platform.system() == "Linux" or platform.system() == "Windows"):
        #     print(f"Xformers libraries for Torch2 are not available for {platform.system()} yet, disabling.")
        #     use_torch2 = False

        requirements = os.path.join(os.path.dirname(os.path.realpath(__file__)), "requirements.txt")
        # Open requirements file and read lines
        with open(requirements, 'r') as f:
            lines = f.readlines()

        # Create dictionary to store package names and version numbers
        reqs_dict = {}

        # Regular expression to match package names and version numbers
        pattern = r'^(?P<package_name>[\w-]+)(\[(?P<extras>[\w\s,-]+)\])?((?P<operator>==|~=)(?P<version>(\d+\.)*\d+([ab]\d+)?)(\.\w+)?(\.\w+(-\d+)?)?)?$'

        # Loop through each line in the requirements file
        for line in lines:
            # Strip whitespace and comments
            line = line.strip()
            if line.startswith('#'):
                continue
            # Use regular expression to extract package name and version number
            match = re.match(pattern, line)
            if match:
                package_name = match.group('package_name')
                version = match.group('version')
                # Split version number into three integers
                if version:
                    version_list = version.split('.')[:3]
                    # Remove any non-digit characters from the third version value
                    version_list[2] = ''.join(filter(str.isdigit, version_list[2]))
                    version_tuple = tuple(map(int, version_list))
                else:
                    version_tuple = None
                # Add package name and version tuple to dictionary
                reqs_dict[package_name] = version_tuple

        versioned_libs = {
            "torch": "1.13.1+cu116",
            "torchvision": "0.14.1+cu116",
            "xformers": "0.0.17",
        }

        for module, min_ver in versioned_libs.items():
            has_module = importlib.util.find_spec(module) is not None
            installed_ver = str(importlib_metadata.version(module)) if has_module else None

            if not installed_ver:
                print(f"[!] {module} NOT installed.")
                launch_errors.append(f"{module} not installed.")
            else:
                installed_split = re.split(r"[.+]", installed_ver)
                min_split = re.split(r"[.+]", min_ver)
                error_detected = False
                for (i_ver, m_ver) in zip(installed_split, min_split):
                    if i_ver > m_ver:
                        break
                    if i_ver is None or i_ver < m_ver:
                        error_detected = True
                        break
                if error_detected:
                    print(f"[!] {module} version {installed_ver} installed.")
                    launch_errors.append(f"Incorrect version of {module} installed.")
                else:
                    print(f"[+] {module} version {installed_ver} installed.")

        # Loop through each required package and check if it is installed
        non_torch_checks = ["accelerate", "bitsandbytes", "diffusers", "transformers"]
        for installed_ver in non_torch_checks:
            check_ver = "N/A"
            status = "[ ]"
            try:
                check_available = importlib.util.find_spec(installed_ver) is not None
                if check_available:
                    check_ver = importlib_metadata.version(installed_ver)
                    check_version = tuple(map(int, re.split(r"[.+]", check_ver)[:3]))

                    if installed_ver in reqs_dict:
                        req_version = reqs_dict[installed_ver]
                        if req_version is None or check_version >= req_version:
                            status = "[+]"
                        else:
                            status = "[!]"
                            launch_errors.append(f"Incorrect version of {installed_ver} installed.")

            except importlib_metadata.PackageNotFoundError:
                print(f"No package for {installed_ver}")
                check_available = False
            if not check_available:
                status = "[!]"
                print(f"{status} {installed_ver} NOT installed.")
                launch_errors.append(f"{installed_ver} not installed.")
            else:
                print(f"{status} {installed_ver} version {check_ver} installed.")

        try:
            from modules.shared import cmd_opts
            xformers_flag = cmd_opts["xformers"]
            if not xformers_flag:
                error = "XFORMERS FLAG IS DISABLED, XFORMERS MUST BE ENABLED IN AUTO1111!"
                print(error)
                launch_errors.append(error)
        except:
            pass

        if len(launch_errors):
            print("Launch errors detected: ")
            print("\n".join(launch_errors))
            os.environ["ERRORS"] = json.dumps(launch_errors)
        else:
            os.environ["ERRORS"] = ""

    base_dir = os.path.dirname(os.path.realpath(__file__))
    revision = ""
    app_revision = ""

    try:
        repo = git.Repo(base_dir)
        revision = repo.rev_parse("HEAD")
        app_repo = git.Repo(os.path.join(base_dir, "../../..", ".."))
        app_revision = app_repo.rev_parse("HEAD")
    except:
        pass

    print("")
    print("#######################################################################################################")
    print("Initializing Dreambooth")
    print("If submitting an issue on github, please provide the below text for debugging purposes:")
    print("")
    print(f"Python revision: {sys.version}")
    print(f"Dreambooth revision: {revision}")
    print(f"SD-WebUI revision: {app_revision}")
    print("")
    dreambooth_skip_install = os.environ.get('DREAMBOOTH_SKIP_INSTALL', False)

    try:
        requirements_file = os.environ.get('REQS_FILE', "requirements_versions.txt")
        if requirements_file == req_file:
            dreambooth_skip_install = True
    except:
        pass

    if not dreambooth_skip_install:
        name = "Dreambooth"
        install_requirements(req_file, name)

    python = sys.executable

    # Check for "different" B&B Files and copy only if necessary
    if os.name == "nt":
        try:
            bnb_src = os.path.join(os.path.dirname(os.path.realpath(__file__)), "bitsandbytes_windows")
            bnb_dest = os.path.join(sysconfig.get_paths()["purelib"], "bitsandbytes")
            filecmp.clear_cache()
            for file in os.listdir(bnb_src):
                src_file = os.path.join(bnb_src, file)
                if file == "main.py" or file == "paths.py":
                    dest = os.path.join(bnb_dest, "cuda_setup")
                else:
                    dest = bnb_dest
                shutil.copy2(src_file, dest)
        except:
            pass

    check_versions()

    print("")
    print("#######################################################################################################")
    try:
        from modules import safe
        safe.load = safe.unsafe_torch_load
        import torch
        torch.load = safe.unsafe_torch_load
    except:
        pass


def install_requirements(req_file, package_name):
    try:
        print(f"Checking {package_name} requirements...")
        output = subprocess.check_output(
            [sys.executable, "-m", "pip", "install", "-r", req_file],
            universal_newlines=True
        )
        for line in output.split('\n'):
            if 'already satisfied' not in line:
                print(line)
    except subprocess.CalledProcessError:
        print(f"Failed to install {package_name} requirements.")
