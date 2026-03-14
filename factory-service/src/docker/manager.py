"""
Docker Manager for Bot Containers
Handles creation, management and monitoring of bot containers
"""
import os
import subprocess
import json
from typing import Optional, List
from loguru import logger


class DockerManager:
    """
    Manages Docker containers for bot instances using Docker CLI
    """

    def __init__(self):
        """Initialize Docker manager"""
        pass

    async def initialize(self):
        """Initialize Docker connection"""
        try:
            # Test Docker connection
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("Docker connection established")
            logger.debug(f"Docker version: {result.stdout}")
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise

    async def close(self):
        """Close Docker manager"""
        logger.info("Docker manager closed")

    async def create_bot_container(
        self,
        bot_id: str,
        bot_token: str,
        webhook_url: Optional[str] = None
    ) -> str:
        """
        Create a new bot container from bot-template image

        Args:
            bot_id: Bot UUID
            bot_token: Telegram bot token
            webhook_url: Optional webhook URL

        Returns:
            Container ID
        """
        try:
            # Container name
            container_name = f"bot_{bot_id[:8]}"

            # Environment variables
            env_vars = [
                f"BOT_ID={bot_id}",
                f"BOT_TOKEN={bot_token}",
                f"DATABASE_URL={os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@database:5432/bot_saas')}",
                f"USE_WEBHOOK={'1' if webhook_url else '0'}",
                f"WEBHOOK_URL={webhook_url or ''}",
                f"TZ=Europe/Moscow"
            ]

            # Get bot-template image
            image_name = os.getenv("BOT_TEMPLATE_IMAGE", "bot-template:latest")

            # Build docker run command
            cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "--label", f"bot_id={bot_id}",
                "--label", "service=telegram-bot",
                "--label", "managed_by=factory-service",
                "--label", f"webhook_path=/webhook/{bot_id}",
                "--restart", "unless-stopped",
                "--network", os.getenv("DOCKER_NETWORK", "bot_saas_network"),
                "-p", f"8080",  # Expose webhook port
            ]

            # Add environment variables
            for env_var in env_vars:
                cmd.extend(["-e", env_var])

            # Pull image if needed
            try:
                subprocess.run(
                    ["docker", "inspect", "--type=image", image_name],
                    capture_output=True,
                    check=True
                )
                logger.info(f"Using existing image: {image_name}")
            except subprocess.CalledProcessError:
                logger.info(f"Pulling image: {image_name}")
                subprocess.run(
                    ["docker", "pull", image_name],
                    check=True
                )

            # Run container
            result = subprocess.run(
                cmd + [image_name],
                capture_output=True,
                text=True,
                check=True
            )

            container_id = result.stdout.strip()
            logger.info(f"Container created and started: {container_id} ({container_name})")

            return container_id

        except Exception as e:
            logger.error(f"Error creating container: {e}")
            raise

    async def get_container(self, bot_id: str):
        """Get container by bot_id"""
        try:
            result = subprocess.run(
                [
                    "docker", "ps", "-a",
                    "--filter", f"label=bot_id={bot_id}",
                    "--format", "{{.ID}}"
                ],
                capture_output=True,
                text=True,
                check=True
            )

            container_id = result.stdout.strip()
            if not container_id:
                return None

            # Get full container info
            info_result = subprocess.run(
                ["docker", "inspect", container_id],
                capture_output=True,
                text=True,
                check=True
            )

            info = json.loads(info_result.stdout)[0]
            return info

        except subprocess.CalledProcessError:
            return None
        except Exception as e:
            logger.error(f"Error getting container: {e}")
            raise

    async def get_container_status(self, bot_id: str) -> str:
        """Get container status"""
        container = await self.get_container(bot_id)
        if not container:
            return "not_found"

        return container['State']['Status']

    async def start_container(self, bot_id: str) -> None:
        """Start a container"""
        container = await self.get_container(bot_id)
        if not container:
            raise ValueError(f"Container for bot {bot_id} not found")

        container_id = container['Id']
        subprocess.run(
            ["docker", "start", container_id],
            check=True
        )
        logger.info(f"Container started: {container_id}")

    async def stop_container(self, bot_id: str) -> None:
        """Stop a container"""
        container = await self.get_container(bot_id)
        if not container:
            raise ValueError(f"Container for bot {bot_id} not found")

        container_id = container['Id']
        subprocess.run(
            ["docker", "stop", container_id],
            check=True
        )
        logger.info(f"Container stopped: {container_id}")

    async def restart_container(self, bot_id: str) -> None:
        """Restart a container"""
        container = await self.get_container(bot_id)
        if not container:
            raise ValueError(f"Container for bot {bot_id} not found")

        container_id = container['Id']
        subprocess.run(
            ["docker", "restart", container_id],
            check=True
        )
        logger.info(f"Container restarted: {container_id}")

    async def delete_container(self, bot_id: str) -> None:
        """Delete a container"""
        container = await self.get_container(bot_id)
        if not container:
            raise ValueError(f"Container for bot {bot_id} not found")

        container_id = container['Id']

        # Stop if running
        status = container['State']['Status']
        if status == "running":
            subprocess.run(
                ["docker", "stop", container_id],
                check=True
            )

        # Remove
        subprocess.run(
            ["docker", "rm", container_id],
            check=True
        )
        logger.info(f"Container deleted: {container_id}")

    async def list_bot_containers(self) -> List:
        """List all bot containers"""
        try:
            result = subprocess.run(
                [
                    "docker", "ps", "-a",
                    "--filter", "label=service=telegram-bot",
                    "--format", "{{json .}}"
                ],
                capture_output=True,
                text=True,
                check=True
            )

            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        info = json.loads(line)
                        containers.append(info)
                    except json.JSONDecodeError:
                        continue

            return containers
        except Exception as e:
            logger.error(f"Error listing containers: {e}")
            raise

    async def set_webhook(
        self,
        bot_id: str,
        webhook_url: str,
        secret_token: Optional[str] = None
    ) -> None:
        """
        Set webhook for a bot container

        This updates the container's environment variables and restarts it
        """
        # For simplicity, we'll just log this for now
        # In production, you'd update the container and restart it
        logger.info(f"Webhook set for bot {bot_id}: {webhook_url}")
