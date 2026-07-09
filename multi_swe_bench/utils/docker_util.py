import logging
import re
from pathlib import Path
from typing import Optional

import docker

docker_client = docker.from_env()


def _is_removal_in_progress(error: docker.errors.APIError) -> bool:
    return (
        getattr(error, "status_code", None) == 409
        and "removal of container" in str(error)
        and "is already in progress" in str(error)
    )


def _remove_container(container) -> None:
    try:
        container.remove()
    except docker.errors.NotFound:
        return
    except docker.errors.APIError as e:
        if _is_removal_in_progress(e):
            return
        raise


def _sanitize_mswebench_name_part(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _mswebench_image_candidates(image_name: str) -> list[str]:
    name, sep, tag = image_name.partition(":")
    if not sep or "/" not in name:
        return []

    org, repo = name.split("/", 1)
    candidates = [
        f"mswebench/{org}_m_{repo}:{tag}",
        (
            "mswebench/"
            f"{_sanitize_mswebench_name_part(org)}"
            "_m_"
            f"{_sanitize_mswebench_name_part(repo)}"
            f":{tag}"
        ),
    ]

    return list(dict.fromkeys(candidates))


def exists(image_name: str) -> bool:
    try:
        docker_client.images.get(image_name)
        return True
    except docker.errors.ImageNotFound:
        return False


def exists_or_alias_mswebench(image_name: str, logger: logging.Logger) -> bool:
    if exists(image_name):
        return True

    for candidate in _mswebench_image_candidates(image_name):
        try:
            image = docker_client.images.get(candidate)
        except docker.errors.ImageNotFound:
            continue

        repo, tag = image_name.rsplit(":", 1)
        image.tag(repo, tag=tag)
        logger.info(
            "Image `%s` found as `%s`; tagged local alias `%s`.",
            image_name,
            candidate,
            image_name,
        )
        return True

    return False


def build(
    workdir: Path,
    dockerfile_name: str,
    image_full_name: str,
    logger: logging.Logger,
    buildargs: Optional[dict[str, str]] = None,
):
    workdir = str(workdir)
    logger.info(
        f"Start building image `{image_full_name}`, working directory is `{workdir}`"
    )
    try:
        build_logs = docker_client.api.build(
            path=workdir,
            dockerfile=dockerfile_name,
            tag=image_full_name,
            rm=True,
            forcerm=True,
            decode=True,
            encoding="utf-8",
            buildargs=buildargs,
        )

        for log in build_logs:
            if "stream" in log:
                logger.info(log["stream"].strip())
            elif "error" in log:
                error_message = log["error"].strip()
                logger.error(f"Docker build error: {error_message}")
                raise RuntimeError(f"Docker build failed: {error_message}")
            elif "status" in log:
                logger.info(log["status"].strip())
            elif "aux" in log:
                logger.info(log["aux"].get("ID", "").strip())

        logger.info(f"image({workdir}) build success: {image_full_name}")
    except docker.errors.BuildError as e:
        logger.error(f"build error: {e}")
        raise e
    except Exception as e:
        logger.error(f"Unknown build error occurred: {e}")
        raise e


def run(
    image_full_name: str,
    run_command: str,
    output_path: Optional[Path] = None,
    global_env: Optional[list[str]] = None,
) -> str:
    container = docker_client.containers.run(
        image=image_full_name,
        command=run_command,
        remove=False,
        detach=True,
        stdout=True,
        stderr=True,
        environment=global_env,
    )

    output = ""
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            for line in container.logs(stream=True, follow=True):
                line_decoded = line.decode("utf-8")
                f.write(line_decoded)
                output += line_decoded
    else:
        container.wait()
        output = container.logs().decode("utf-8")

    _remove_container(container)

    return output
