import asyncio
import json
import aiofiles
import os
import httpx
import xml.etree.ElementTree as ET
import yaml

from gi.repository import GLib, GObject
from waydroid_helper.util.SubprocessManager import SubprocessManager
from waydroid_helper.util.Task import Task
from waydroid_helper.util.arch import host
from waydroid_helper.waydroid import Waydroid
from enum import IntEnum


class ExtentionManagerState(IntEnum):
    UNINITIALIZED = 0
    READY = 1


# TODO 1. 检查 arch 和 android_version
#      2. 避免多次重启
#      3. 进度条, 完成提醒
#      4. prop 修改放在 yaml 里, 不要单独文件了
class PackageManager(GObject.Object):
    state = GObject.Property(type=object)
    waydroid: Waydroid = GObject.Property(type=object)
    available_extensions = {}
    installed_packages = {}
    arch = host()
    remote = "https://github.com/ayasa520/extensions/raw/master/"
    extensions_json = []
    storage_dir = os.path.join(GLib.get_user_data_dir(), os.getenv("PROJECT_NAME"))
    cache_dir = os.path.join(GLib.get_user_cache_dir(), os.getenv("PROJECT_NAME"))
    _task = Task()
    _subprocess = SubprocessManager()
    # TODO 同时安装多个扩展的问题, 最好做到可以并发下载, 串行安装
    _semaphore_1 = asyncio.Semaphore(1)
    _semaphore_2 = asyncio.Semaphore(1)

    async def fetch_snapshot(self, name, version):
        print(self.available_extensions[f"{name}-{version}"])

    async def fetch_extension_json(self):
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(self.remote + "extensions.json")
                if response.status_code == 200:
                    return response.json()
                else:
                    print(
                        f"Failed to fetch JSON from, status code: {response.status_code}"
                    )
                    return None
            except AssertionError as e:
                pass

    async def save_extension_json(self):
        json_path = os.path.join(self.storage_dir, "extensions.json")
        # json_cache_path = os.path.join(self.cache_dir, "extensions.json")
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        async with aiofiles.open(json_path, "w") as f:
            json_str = json.dumps(self.extensions_json, ensure_ascii=False, indent=4)
            await f.write(json_str)

        # await self._subprocess.run(
        #     f"pkexec waydroid-cli mkdir  {os.path.dirname(json_path)}"
        # )

        # await self._subprocess.run(
        #     f"pkexec waydroid-cli copy {json_cache_path} {json_path}"
        # )

    async def update_extension_json(self):
        extensions = await self.fetch_extension_json()
        self.extensions_json = extensions
        if extensions:
            self._task.create_task(self.save_extension_json())

    def is_installed(self, name, version=None):
        package = self.installed_packages.get(name)
        if package is None:
            return False
        return version is None or package.get("version") == version

    async def init_manager(self):
        json_path = os.path.join(self.storage_dir, "extensions.json")
        if not os.path.exists(json_path):
            await self.update_extension_json()
        else:
            async with aiofiles.open(json_path, "r") as f:
                self.extensions_json = json.loads(await f.read())
        self.grab_meta()
        await self.load_installed()
        self.state = ExtentionManagerState.READY

    def __init__(self):
        super().__init__()
        self.state = ExtentionManagerState.UNINITIALIZED
        self._task.create_task(self.init_manager())
        os.makedirs(self.storage_dir, exist_ok=True)

    async def load_installed(self):
        directory = os.path.join(self.storage_dir, "local")
        if not os.path.exists(directory):
            return
        for folder_name in os.listdir(directory):
            folder_path = os.path.join(directory, folder_name)

            # 检查是否是文件夹
            if os.path.isdir(folder_path):
                # 指定 desc.json 的路径
                desc_path = os.path.join(folder_path, "desc")

                # 检查 desc.json 文件是否存在
                if os.path.isfile(desc_path):
                    # 读取 desc.json 文件
                    async with aiofiles.open(desc_path, "r") as f:
                        content = await f.read()
                        desc_data = json.loads(content)
                        self.installed_packages[desc_data["name"]] = desc_data

    def get_data(self):
        return self.extensions_json

    def grab_meta(self):
        for item1 in self.extensions_json:
            for item2 in item1["list"]:
                for item3 in item2["list"]:
                    if "list" in item3.keys():
                        path = f'{item1["path"]}/{item2["path"]}/{item3["path"]}'
                        extension = item3["list"]
                        extension = {
                            f'{each["name"]}-{each["version"]}': {
                                **each,
                                **{"path": f"{path}/{each['path']}"},
                            }
                            for each in extension
                        }
                    else:
                        path = f'{item1["path"]}/{item2["path"]}/{item3["path"]}'
                        extension = {
                            f'{item3["name"]}-{item3["version"]}': {
                                **item3,
                                **{"path": path},
                            }
                        }
                    self.available_extensions.update(extension)

    def get_package_info(self, name, version=None):
        if version is not None:
            package = self.available_extensions.get(f"{name}-{version}")
            return package
        for package in self.available_extensions.values():
            if name in package.get("provides", []):
                return package
        return None

    def check_conflicts(self, package_info=None, name=None, version=None):
        conflicts = set()
        if package_info is None:
            package_info = self.get_package_info(name=name, version=version)
        for installed_package in self.installed_packages.values():
            # 检查 package_info 的 conflicts 列表
            for conflict in package_info.get("conflicts", []):
                if conflict == installed_package[
                    "name"
                ] or conflict in installed_package.get("provides", []):
                    conflicts.add(installed_package["name"])
            # 检查已安装包的 conflicts 列表
            for conflict in installed_package.get("conflicts", []):
                if conflict == package_info["name"] or conflict in package_info.get(
                    "provides", []
                ):
                    conflicts.add(installed_package["name"])
        return conflicts

    def list_installed(self):
        return self.installed_packages

    # def check_dependencies(self, package_info):
    #     """检查包的依赖"""
    #     missing_dependencies = []
    #     for dependency in package_info.get("dependencies", []):
    #         if dependency not in self.installed_packages.keys() and not any(
    #             dependency in pkg.get("provides", [])
    #             for pkg in self.installed_packages.values()
    #         ):
    #             missing_dependencies.append(dependency)
    #     return missing_dependencies

    async def download_file(self, client, url, dest_path, md5=None, retries=3, delay=2):
        attempt = 0
        while attempt < retries:
            try:
                response = await client.get(url)
                assert response.content, "Downloaded content is empty"

                if not os.path.exists(os.path.dirname(dest_path)):
                    os.makedirs(os.path.dirname(dest_path))

                async with aiofiles.open(dest_path, mode="wb") as f:
                    await f.write(response.content)

                if md5 is not None:
                    result = await self._subprocess.run(f'md5sum "{dest_path}"')
                    actual_md5 = result["stdout"].split()[0]
                    if actual_md5 != md5:
                        raise ValueError(
                            f"MD5 mismatch: expected {md5}, got {actual_md5}"
                        )

                print(f"File downloaded and saved to {dest_path}")
                return
            except (
                httpx.HTTPStatusError,
                httpx.RequestError,
                AssertionError,
                ValueError,
            ) as e:
                attempt += 1
                if attempt < retries:
                    print(
                        f"Attempt {attempt} failed: {e}. Retrying in {delay} seconds..."
                    )
                    await asyncio.sleep(delay)
                else:
                    print(
                        f"All {retries} attempts failed. Could not download the file."
                    )
                    raise

    def get_all_files_relative(self, directory):
        all_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.relpath(os.path.join(root, file), directory)
                all_files.append(file_path)
        return all_files

    async def download(self, package_info):
        async with httpx.AsyncClient(follow_redirects=True) as client:
            tasks = []
            for file in package_info["files"]:
                url = f'{self.remote}{package_info["path"]}/{file}'
                dest = f'{self.cache_dir}/extensions/{package_info["name"]}/{file}'
                tasks.append(self.download_file(client, url, dest))

            if f"source_{self.arch}" in package_info.keys():
                _source = f"source_{self.arch}"
                _md5sums = f"md5sums_{self.arch}"
            else:
                _source = "source"
                _md5sums = f"md5sums"

            for source, md5 in zip(package_info[_source], package_info[_md5sums]):
                file_name = source.split("::")[0]
                url = source.split("::")[1]
                file_path = os.path.join(
                    self.cache_dir, "extensions", package_info["name"], file_name
                )
                if os.path.exists(file_path):
                    result = await self._subprocess.run(f'md5sum "{file_path}"')
                    actual_md5 = result["stdout"].split()[0]
                    if actual_md5 == md5:
                        continue
                    else:
                        tasks.append(self.download_file(client, url, file_path))
                else:
                    tasks.append(self.download_file(client, url, file_path))

            await asyncio.gather(*tasks)

    async def install_package(
        self, name, version, remove_conflicts=False, install_dependencies=False
    ):
        async with self._semaphore_1:
            package_info = self.get_package_info(name, version)
            if package_info is None:
                print(f"Package {name} not found.")
                return
            # 检查冲突
            conflicts = self.check_conflicts(package_info)
            if conflicts:
                if remove_conflicts:
                    await self.remove_packages(conflicts)
                else:
                    print(
                        f"Package {package_info['name']} conflicts with installed packages: {', '.join(conflicts)}."
                    )
                    return
            # 检查架构
            if "arch" in package_info.keys() and self.arch not in package_info["arch"]:
                raise ValueError("Hardware architecture mismatch")

        # 检查依赖
        # missing_dependencies = self.check_dependencies(package_info)
        # if missing_dependencies:
        #     if install_dependencies:
        #         for dependency in missing_dependencies:
        #             self.install_package(
        #                 dependency, remove_conflicts, install_dependencies
        #             )
        #     else:
        #         print(
        #             f"Package {package_info['name']} is missing dependencies: {', '.join(missing_dependencies)}."
        #         )
        #         return

        # 下载
        await self.download(package_info)

        async with self._semaphore_2:
            # 调用 installer
            startdir = os.path.join(self.cache_dir, "extensions", package_info["name"])
            pkgdir = os.path.join(startdir, "pkg")
            package = (
                f'{startdir}/{package_info["name"]}-{package_info["version"]}.tar.gz'
            )
            await self._subprocess.run(
                f'waydroid-cli call_package "{startdir}" "{package_info['name']}" "{package_info['version']}"',
                env={"CARCH": self.arch, "SDK": "30"},
            )
            if "install" in package_info.keys():
                await self.pre_install(package_info)
            await self._subprocess.run(f'pkexec waydroid-cli install "{package}"')

            installed_files = self.get_all_files_relative(pkgdir)

            # desc_cache_path = os.path.join(startdir, "desc")
            local_dir = os.path.join(
                self.storage_dir, "local", f"{package_info['name']}"
            )
            desc_path = os.path.join(local_dir, "desc")
            package_info = {
                **package_info,
                **{"installed_files": installed_files},
            }
            # 应用 prop
            if os.path.exists(os.path.join(startdir, "prop.json")):
                async with aiofiles.open(
                    os.path.join(startdir, "prop.json"), mode="r"
                ) as f:
                    content = await f.read()
                    props = json.loads(content)
                    await self.waydroid.set_extension_props(props)

                package_info = {
                    **package_info,
                    **{"props": list(props.keys())},
                }

            os.makedirs(local_dir, exist_ok=True)
            async with aiofiles.open(desc_path, mode="w") as f:
                content = json.dumps(package_info)
                await f.write(content)

            if "install" in package_info.keys():
                cache_install = os.path.join(startdir, package_info["install"])
                local_install = os.path.join(local_dir, "install")
                await self._subprocess.run(
                    f"install -Dm 755 {cache_install} {local_install}"
                )

            # 标记已安装包
            # await self._subprocess.run(f"pkexec waydroid-cli mkdir {local_dir}")
            # await self._subprocess.run(
            #     f"pkexec waydroid-cli copy {desc_cache_path} {local_dir}"
            # )

            self.installed_packages[package_info["name"]] = package_info
            print(f"Package {package_info['name']} installed successfully.")

            # post_install
            if "install" in package_info.keys():
                await self.post_install(package_info)

    async def execute_post_operations(self, info, operation_key: str):
        if operation_key.endswith("install"):
            install_path = os.path.join(
                self.cache_dir, "extensions", info["name"], info["install"]
            )
        else:
            install_path = os.path.join(
                self.storage_dir, "local", info["name"], "install"
            )

        async with aiofiles.open(install_path, "r") as f:
            content = await f.read()
            yml = yaml.safe_load(content)

        if operation_key not in yml:
            return

        operations = yml[operation_key]
        for operation in operations:
            for func_name, args in operation.items():
                command = await self.generate_command(func_name, args)
                if command:
                    await self._subprocess.run(
                        command,
                        env={
                            "pkgdir": os.path.join(
                                self.cache_dir, "extensions", info["name"], "pkg"
                            )
                        },
                    )
                else:
                    print(f"Unsupported function or invalid arguments: {func_name}")

    async def get_apk_path(self, apks: list) -> str:
        paths = []
        data_dir = os.path.join(GLib.get_user_data_dir(), "waydroid/data")
        package_path = os.path.join(data_dir, "system/packages.xml")
        async with aiofiles.open(package_path, "r") as f:
            content = await f.read()
        tree = ET.fromstring(content)
        for package in tree.findall("package"):
            name = package.get("name")
            code_path = package.get("codePath")
            if name in apks:
                paths.append(f"app/{os.path.basename(os.path.dirname(code_path))}")
                apks.remove(name)
                if len(apks) == 0:
                    break
        paths = ['"' + path + '"' for path in paths]
        return " ".join(paths)

    async def generate_command(self, func_name, args):
        command_map = {
            "rm_overlay_rw": "pkexec waydroid-cli rm_overlay_rw {paths}",
            "rm_data": "pkexec waydroid-cli rm_data {paths}",
            "cp_to_data": 'pkexec waydroid-cli cp_to_data "{src}" "{dest}"',
            "rm_apk": "pkexec waydroid-cli rm_data {paths}",
        }

        if func_name in command_map:
            if func_name == "cp_to_data":
                src = args.get("src")
                dest = args.get("dest")
                if src and dest:
                    return command_map[func_name].format(src=src, dest=dest)
            elif func_name == "rm_apk":
                paths = await self.get_apk_path(args)
                if paths.strip()=="":
                    return None
                return command_map[func_name].format(paths=paths)
            else:
                paths = " ".join(['"' + path + '"' for path in args])
                return command_map[func_name].format(paths=paths)

        return None

    async def pre_install(self, info):
        await self.execute_post_operations(info, "pre_install")

    async def post_install(self, info):
        await self.execute_post_operations(info, "post_install")

    async def post_remove(self, info):
        await self.execute_post_operations(info, "post_remove")

    async def remove_package(self, package_name):
        """移除包"""
        if package_name in self.installed_packages:
            await self._subprocess.run(
                f'pkexec waydroid-cli rm_overlay {" ".join(self.installed_packages[package_name]["installed_files"])}'
            )
            # await self._subprocess.run(
            #     f"pkexec waydroid-cli rm {os.path.join(self.storage_dir, 'local', package_name)}"
            # )
            if "props" in self.installed_packages[package_name].keys():
                await self.waydroid.remove_extension_props(
                    self.installed_packages[package_name]["props"]
                )
            if "install" in self.installed_packages[package_name].keys():
                await self.post_remove(self.installed_packages[package_name])
            await self._subprocess.run(
                f"rm -rf {os.path.join(self.storage_dir, 'local', package_name)}"
            )
            # await asyncio.gather(coro1, coro2, coro3)

            del self.installed_packages[package_name]
            print(f"Package {package_name} removed successfully.")
        else:
            print(f"Package {package_name} is not installed.")

    async def remove_packages(self, package_names):
        for pkg in package_names:
            print("remove", pkg)
            await self.remove_package(pkg)
