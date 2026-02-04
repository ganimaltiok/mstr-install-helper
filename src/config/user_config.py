"""
MicroStrategy dedicated user configuration module.

Creates and configures a dedicated Linux user for MicroStrategy installation
following security best practices.
"""

import os
import pwd
import grp
from ..utils.command_runner import CommandRunner
from ..utils.logger import Logger
from ..utils.backup_manager import BackupManager


class UserConfig:
    """Configure dedicated MicroStrategy user."""
    
    def __init__(self):
        self.logger = Logger()
        self.runner = CommandRunner()
        self.backup = BackupManager()
        self.sudoers_file = '/etc/sudoers.d/mstr-user'
    
    def user_exists(self, username):
        """Check if user already exists."""
        try:
            pwd.getpwnam(username)
            return True
        except KeyError:
            return False
    
    def create_user(self, username='mstr', create_home=True):
        """
        Create dedicated MicroStrategy user.
        
        Args:
            username: Username to create (default: mstr)
            create_home: Create home directory (default: True)
        
        Returns:
            dict: Result with success status and details
        """
        result = {
            'success': False,
            'username': username,
            'message': '',
            'details': {}
        }
        
        try:
            # Check if user already exists
            if self.user_exists(username):
                self.logger.warning(f"User '{username}' already exists")
                result['success'] = True
                result['message'] = f"User '{username}' already exists"
                
                # Get user info
                user_info = pwd.getpwnam(username)
                result['details'] = {
                    'uid': user_info.pw_uid,
                    'gid': user_info.pw_gid,
                    'home': user_info.pw_dir,
                    'shell': user_info.pw_shell
                }
                return result
            
            # Create user
            self.logger.info(f"Creating user '{username}'...")
            
            cmd_parts = ['useradd']
            if create_home:
                cmd_parts.append('-m')  # Create home directory
            cmd_parts.extend([
                '-s', '/bin/bash',  # Set bash as default shell
                '-c', '"MicroStrategy Service Account"',  # Comment (quoted for spaces)
                username
            ])
            
            rc, output, error = self.runner.run(' '.join(cmd_parts))
            success = (rc == 0)
            
            if not success:
                result['message'] = f"Failed to create user: {error}"
                self.logger.error(result['message'])
                return result
            
            self.logger.success(f"User '{username}' created successfully")
            
            # Get user info
            user_info = pwd.getpwnam(username)
            result['details'] = {
                'uid': user_info.pw_uid,
                'gid': user_info.pw_gid,
                'home': user_info.pw_dir,
                'shell': user_info.pw_shell
            }
            
            result['success'] = True
            result['message'] = f"User '{username}' created successfully"
            
            return result
            
        except Exception as e:
            result['message'] = f"Error creating user: {str(e)}"
            self.logger.error(result['message'])
            return result
    
    def set_user_password(self, username, password):
        """
        Set password for user.
        
        Args:
            username: Username
            password: Password to set
        
        Returns:
            dict: Result with success status
        """
        result = {
            'success': False,
            'username': username,
            'message': ''
        }
        
        try:
            # Check if user exists
            if not self.user_exists(username):
                result['message'] = f"User '{username}' does not exist"
                self.logger.error(result['message'])
                return result
            
            self.logger.info(f"Setting password for '{username}'...")
            
            # Use chpasswd to set password
            cmd = f"echo '{username}:{password}' | chpasswd"
            rc, output, error = self.runner.run(cmd, shell=True)
            success = (rc == 0)
            
            if not success:
                result['message'] = f"Failed to set password: {error}"
                self.logger.error(result['message'])
                return result
            
            self.logger.success(f"Password set for '{username}'")
            result['success'] = True
            result['message'] = f"Password configured successfully"
            
            return result
            
        except Exception as e:
            result['message'] = f"Error setting password: {str(e)}"
            self.logger.error(result['message'])
            return result
    
    def configure_sudo_access(self, username='mstr'):
        """
        Configure sudo access for MicroStrategy user.
        
        Args:
            username: Username to configure
        
        Returns:
            dict: Result with success status
        """
        result = {
            'success': False,
            'username': username,
            'message': ''
        }
        
        try:
            # Check if user exists
            if not self.user_exists(username):
                result['message'] = f"User '{username}' does not exist"
                self.logger.error(result['message'])
                return result
            
            self.logger.info(f"Configuring sudo access for '{username}'...")
            
            # Create sudoers file for mstr user
            sudoers_content = f"""# MicroStrategy user sudo configuration
# Created by mstr-helper
# Allows full sudo access for MicroStrategy installation and management

{username} ALL=(ALL) NOPASSWD: ALL

# Disable requiretty for this user (needed for automation)
Defaults:{username} !requiretty
"""
            
            # Write sudoers file
            sudoers_path = f'/etc/sudoers.d/{username}-mstr'
            
            try:
                with open(sudoers_path, 'w') as f:
                    f.write(sudoers_content)
                
                # Set correct permissions (must be 0440 or 0400)
                os.chmod(sudoers_path, 0o440)
                
                # Verify syntax with visudo
                rc, output, error = self.runner.run(
                    f'visudo -c -f {sudoers_path}'
                )
                success = (rc == 0)
                
                if not success:
                    # Remove invalid file
                    os.remove(sudoers_path)
                    result['message'] = f"Invalid sudoers syntax: {error}"
                    self.logger.error(result['message'])
                    return result
                
                self.logger.success(f"Sudo access configured for '{username}'")
                result['success'] = True
                result['message'] = f"Sudo access configured successfully"
                result['sudoers_file'] = sudoers_path
                
            except Exception as e:
                result['message'] = f"Error writing sudoers file: {str(e)}"
                self.logger.error(result['message'])
                return result
            
            return result
            
        except Exception as e:
            result['message'] = f"Error configuring sudo: {str(e)}"
            self.logger.error(result['message'])
            return result
    
    def setup_home_directory(self, username='mstr'):
        """
        Setup home directory structure for MicroStrategy.
        
        Args:
            username: Username
        
        Returns:
            dict: Result with success status
        """
        result = {
            'success': False,
            'username': username,
            'message': '',
            'directories': []
        }
        
        try:
            # Get user info
            if not self.user_exists(username):
                result['message'] = f"User '{username}' does not exist"
                self.logger.error(result['message'])
                return result
            
            user_info = pwd.getpwnam(username)
            home_dir = user_info.pw_dir
            uid = user_info.pw_uid
            gid = user_info.pw_gid
            
            self.logger.info(f"Setting up home directory for '{username}'...")
            
            # Create useful directories
            directories = [
                f'{home_dir}/logs',
                f'{home_dir}/scripts',
                f'{home_dir}/backups',
                f'{home_dir}/installers'
            ]
            
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
                os.chown(directory, uid, gid)
                result['directories'].append(directory)
            
            # Setup X11 forwarding for GUI applications
            self.logger.info(f"Configuring X11 forwarding for '{username}'...")
            
            # Create .Xauthority file with correct permissions
            xauthority_file = f'{home_dir}/.Xauthority'
            if not os.path.exists(xauthority_file):
                # Create empty .Xauthority file
                with open(xauthority_file, 'w') as f:
                    pass
                os.chmod(xauthority_file, 0o600)
                os.chown(xauthority_file, uid, gid)
                self.logger.success(f"Created .Xauthority file for X11 forwarding")
            
            # Configure DISPLAY variable in .bashrc
            bashrc_file = f'{home_dir}/.bashrc'
            display_config = '''
# MicroStrategy GUI - X Display Configuration
export DISPLAY=localhost:10.0
'''
            
            # Check if already configured
            bashrc_exists = os.path.exists(bashrc_file)
            if bashrc_exists:
                with open(bashrc_file, 'r') as f:
                    bashrc_content = f.read()
                if 'MicroStrategy GUI - X Display Configuration' not in bashrc_content:
                    # Append to existing .bashrc
                    with open(bashrc_file, 'a') as f:
                        f.write(display_config)
                    os.chown(bashrc_file, uid, gid)
                    self.logger.success(f"Added DISPLAY configuration to .bashrc")
            else:
                # Create .bashrc with DISPLAY config
                with open(bashrc_file, 'w') as f:
                    f.write(display_config)
                os.chmod(bashrc_file, 0o644)
                os.chown(bashrc_file, uid, gid)
                self.logger.success(f"Created .bashrc with DISPLAY configuration")
            
            # Ensure home directory has correct permissions for SSH X11 forwarding
            os.chmod(home_dir, 0o755)
            
            # Set ownership of home directory
            for root, dirs, files in os.walk(home_dir):
                for d in dirs:
                    path = os.path.join(root, d)
                    try:
                        os.chown(path, uid, gid)
                    except:
                        pass
                for f in files:
                    path = os.path.join(root, f)
                    try:
                        os.chown(path, uid, gid)
                    except:
                        pass
            
            self.logger.success(f"Home directory setup complete for '{username}'")
            result['success'] = True
            result['message'] = 'Home directory setup complete'
            result['home_dir'] = home_dir
            
            return result
            
        except Exception as e:
            result['message'] = f"Error setting up home directory: {str(e)}"
            self.logger.error(result['message'])
            return result
    
    def configure_user(self, username='mstr', password='mstr', enable_sudo=True):
        """
        Complete user configuration workflow.
        
        Args:
            username: Username to configure (default: mstr)
            password: Password for the user (default: mstr)
            enable_sudo: Enable sudo access (default: True)
        
        Returns:
            dict: Combined results
        """
        results = {
            'success': False,
            'username': username,
            'steps': {}
        }
        
        try:
            # Step 1: Create user
            self.logger.info("=" * 60)
            self.logger.info("CONFIGURING MICROSTRATEGY USER")
            self.logger.info("=" * 60)
            
            user_result = self.create_user(username)
            results['steps']['user_creation'] = user_result
            
            if not user_result['success']:
                results['message'] = 'User creation failed'
                return results
            
            # Step 2: Set password
            password_result = self.set_user_password(username, password)
            results['steps']['password_setup'] = password_result
            
            if not password_result['success']:
                results['message'] = 'Password setup failed'
                return results
            
            # Step 3: Setup home directory
            home_result = self.setup_home_directory(username)
            results['steps']['home_setup'] = home_result
            
            if not home_result['success']:
                results['message'] = 'Home directory setup failed'
                return results
            
            # Step 4: Configure sudo (if requested)
            if enable_sudo:
                sudo_result = self.configure_sudo_access(username)
                results['steps']['sudo_config'] = sudo_result
                
                if not sudo_result['success']:
                    results['message'] = 'Sudo configuration failed'
                    return results
            
            # All steps successful
            results['success'] = True
            results['message'] = f"User '{username}' configured successfully"
            
            # Summary
            self.logger.info("")
            self.logger.success("=" * 60)
            self.logger.success(f"User '{username}' is ready for MicroStrategy installation")
            self.logger.success("=" * 60)
            self.logger.info("")
            self.logger.info(f"Home Directory: {home_result.get('home_dir', 'N/A')}")
            self.logger.info(f"UID: {user_result['details'].get('uid', 'N/A')}")
            self.logger.info(f"GID: {user_result['details'].get('gid', 'N/A')}")
            self.logger.info(f"Password: {'*' * len(password)}")
            if enable_sudo:
                self.logger.info(f"Sudo Access: Enabled")
            self.logger.info("")
            self.logger.warning(f"SSH Login: ssh {username}@hostname")
            self.logger.warning(f"Local Login: su - {username}")
            self.logger.info("")
            
            return results
            
        except Exception as e:
            results['message'] = f"Error in user configuration: {str(e)}"
            self.logger.error(results['message'])
            return results
    
    def get_user_info(self, username='mstr'):
        """
        Get information about MicroStrategy user.
        
        Args:
            username: Username to query
        
        Returns:
            dict: User information or None
        """
        try:
            if not self.user_exists(username):
                return None
            
            user_info = pwd.getpwnam(username)
            
            return {
                'username': username,
                'uid': user_info.pw_uid,
                'gid': user_info.pw_gid,
                'home': user_info.pw_dir,
                'shell': user_info.pw_shell,
                'gecos': user_info.pw_gecos
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user info: {str(e)}")
            return None
