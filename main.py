"""
Main Entry Point - NitroSense Ultimate Application
Initializes all systems and launches the UI

CRITICAL DESIGN PRINCIPLES:
1. All long-lived objects (Threads, Hardware, Windows) are stored as QApplication attributes (anti-GC)
2. Splash screen is the pre-flight validator and error bridge
3. Global exception handlers catch and log surgically with full context
4. Signal/slot lifecycle is managed with explicit cleanup
5. Hardware watchdog enforces 100% fan on sensor failure

ARCHITECTURE:
The main.py is now modularized for maintainability:
- app_config.py: CLI argument parsing
- app_state.py: Session lock and crash detection
- app_lifecycle.py: Signal handlers and cleanup
- app_exceptions.py: Global exception handlers
- ui/log_viewer.py: Log file viewer dialog

Errors in these modules are caught and logged to prevent silent failures.
"""

import sys
import atexit
from pathlib import Path
from typing import cast, Optional

# Ensure we can import from the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal, QObject

from nitrosense.core.logger import setup_logging, logger
from nitrosense.core.app_config import parse_args
from nitrosense.core.app_state import (
    ensure_session_lock,
    clear_session_lock,
    check_previous_crash,
)
from nitrosense.core.app_exceptions import setup_global_exception_handlers
from nitrosense.core.app_lifecycle import setup_signal_handlers, setup_atexit_cleanup
from nitrosense.core.error_codes import ErrorCode, get_error_description
from nitrosense.core.constants import LOG_CONFIG
from nitrosense.core.single_instance import SingleInstanceLock
from nitrosense.core.startup import StartupManager, finish_startup, handle_startup_failure
from nitrosense.ui.splash import (
    create_splash_screen,
    update_splash,
    log_validation_step,
    QtSplashLogHandler,
)
from nitrosense.i18n import initialize_i18n
from nitrosense.system import NitroSenseSystem
from nitrosense.ui.main_window import NitroSenseApp



class NitroSenseApplication(QApplication):
    """
    Application subclass to own runtime state and long-lived objects.
    
    Attributes:
        single_instance_lock: Prevents multiple instances
        previous_crash_detected: Whether previous run crashed
        system: The NitroSenseSystem instance
        startup_manager: Handles bootstrap and startup validation
        main_window: The main UI window
        hotkeys_manager: Global hotkeys handler (optional)
        log_handler: Qt log handler for splash screen
    """

    single_instance_lock: Optional[SingleInstanceLock]
    previous_crash_detected: bool
    system: Optional[NitroSenseSystem]
    startup_manager: Optional[StartupManager]
    main_window: Optional[NitroSenseApp]
    log_handler: Optional[QtSplashLogHandler]

    def _show_dependency_install_dialog(
        self, missing_apt: dict, missing_pip: dict, splash
    ) -> None:
        """Show dialog asking user if they want to install missing dependencies."""
        try:
            from nitrosense.ui.dependency_install_dialog import DependencyInstallDialog

            # Check if user has saved preference
            saved_preference = DependencyInstallDialog.load_install_preference()
            if saved_preference is True:
                self._perform_auto_install(missing_apt, missing_pip, splash)
                return
            elif saved_preference is False:
                self._continue_after_deps_check(None, splash)
                return

            # No saved preference, show dialog
            dialog = DependencyInstallDialog(missing_apt, missing_pip, splash)
            dialog.installation_complete.connect(
                lambda success, message: self._handle_installation_result(
                    success, message, splash
                )
            )
            dialog.exec()
        except Exception as e:
            logger.error(f"Dependency install dialog error: {e}")
            self._continue_after_deps_check(None, splash)

    def _perform_auto_install(self, missing_apt: dict, missing_pip: dict, splash) -> None:
        """Perform automatic installation without showing dialog."""
        try:
            from nitrosense.resilience.dependency_installer import DependencyInstaller

            installer = DependencyInstaller()

            apt_packages = []
            for packages in missing_apt.values():
                apt_packages.extend(packages)

            pip_packages = []
            for packages in missing_pip.values():
                pip_packages.extend(packages)

            update_splash(splash, "Instalando dependências automaticamente...", 75)

            # Install APT packages
            if apt_packages:
                success, message = installer.install_apt_packages(apt_packages)
                if not success:
                    logger.warning(f"Auto-install failed: {message}")
                    update_splash(splash, f"Instalação automática falhou: {message}", 75)
                    self._continue_after_deps_check(None, splash)
                    return

            # Install pip packages
            if pip_packages:
                success, message = installer.install_pip_packages(pip_packages)
                if not success:
                    logger.warning(f"Auto-install failed: {message}")
                    update_splash(splash, f"Instalação automática falhou: {message}", 75)
                    self._continue_after_deps_check(None, splash)
                    return

            update_splash(splash, "Dependências instaladas automaticamente ✓", 80)
            self._continue_after_deps_check(None, splash)

        except Exception as e:
            logger.error(f"Auto-install error: {e}")
            update_splash(splash, f"Erro na instalação automática: {e}", 75)
            self._continue_after_deps_check(None, splash)

    def _handle_installation_result(self, success: bool, message: str, splash) -> None:
        """Handle the result of dependency installation dialog."""
        try:
            if success:
                update_splash(splash, "Dependências instaladas com sucesso ✓", 80)
            else:
                update_splash(splash, f"Instalação pulada: {message}", 75)

            self._continue_after_deps_check(None, splash)
        except Exception as e:
            logger.error(f"Installation result handling error: {e}")

    def _continue_after_deps_check(self, system, splash) -> None:
        """Continue startup after dependency check/installation."""
        try:
            # Re-run dependency check to verify installation
            system = NitroSenseSystem()

            err, bootstrap_msg = system.bootstrap()
            if err != ErrorCode.SUCCESS:
                logger.error(f"Post-install bootstrap failed: {get_error_description(err)}")
                handle_startup_failure(
                    splash,
                    self,
                    f"Post-install bootstrap failed: {get_error_description(err)}"
                )
                return

            # Continue with final startup
            if self.startup_manager:
                thread = cast(QThread, self.startup_manager.thread)
                finish_startup(splash, self, system, thread)
            else:
                logger.error("Startup manager not initialized")
                handle_startup_failure(splash, self, "Startup manager not initialized")
        except Exception as e:
            logger.error(f"Continuation error: {e}", exc_info=True)
            handle_startup_failure(splash, self, f"Unexpected error during startup: {e}")


def main() -> int:
    """
    Main application entry point.

    CRITICAL LIFECYCLE:
    1. Single instance lock (prevent hardware collision)
    2. Parse CLI arguments  
    3. Check for previous crash
    4. Create QApplication (parent for all objects)
    5. Initialize i18n
    6. Setup exception handlers
    7. Setup signal handlers
    8. Show splash screen
    9. Start background startup thread
    10. Run event loop

    If errors occur at any stage, they are logged and the app exits
    gracefully (never silently crashes).
    """
    try:
        # SINGLE INSTANCE LOCK - MUST BE FIRST (before QApplication)
        single_instance_lock = SingleInstanceLock()
        lock_acquired, lock_msg = single_instance_lock.acquire()

        if not lock_acquired:
            print(f"ERROR: {lock_msg}")
            if "already running" in lock_msg.lower():
                print("Another instance of NitroSense Ultimate is already running.")
                print("To launch another instance, close the existing one first.")
            return 1

        # PARSE ARGUMENTS (before QApplication)
        args = parse_args()
        previous_crash = check_previous_crash()

        # CREATE QAPPLICATION (Parent of everything)
        app: NitroSenseApplication = NitroSenseApplication(sys.argv)
        initialize_i18n("auto")

        # Store state on app
        app.single_instance_lock = single_instance_lock
        app.previous_crash_detected = previous_crash
        app.system = None

        # Setup cleanup handlers
        ensure_session_lock()
        atexit.register(clear_session_lock)
        setup_atexit_cleanup()

        # Setup exception handlers EARLY
        setup_global_exception_handlers(app)
        setup_signal_handlers(app)

        # CREATE AND SHOW SPLASH SCREEN
        splash = None
        use_splash = not args.no_splash

        if use_splash:
            try:
                log_path = Path(LOG_CONFIG["log_dir"]) / LOG_CONFIG["log_file"]
                splash = create_splash_screen(log_path)
                splash.log_handler = QtSplashLogHandler(splash.terminal)
                logger.addHandler(splash.log_handler)
                logger.info("✓ Splash screen created")
                if previous_crash:
                    splash.log_validation(
                        "Detectado fechamento inesperado na última execução. Modo de recuperação ativado.",
                        "WARN",
                    )
            except Exception as exc:
                logger.critical(f"Failed to create splash screen: {exc}", exc_info=True)

        # CREATE STARTUP MANAGER
        app.startup_manager = StartupManager()

        app.startup_manager.update_progress.connect(
            lambda msg, value: update_splash(splash, msg, value) if splash else None
        )
        app.startup_manager.validation_step.connect(
            lambda msg, status: log_validation_step(splash, msg, status) if splash else None
        )
        app.startup_manager.startup_failed.connect(
            lambda reason: handle_startup_failure(splash, app, reason)
        )

        # Store thread reference with explicit type to avoid type checking issues
        startup_thread = cast(QThread, app.startup_manager.thread)
        app.startup_manager.startup_complete.connect(
            lambda system: finish_startup(splash, app, system, startup_thread)
        )
        app.startup_manager.dependency_install_prompt.connect(
            lambda missing_apt, missing_pip: app._show_dependency_install_dialog(
                missing_apt, missing_pip, splash
            )
        )

        app.startup_manager.start()

        # RUN EVENT LOOP WITH EXCEPTION PROTECTION
        logger.info("Starting Qt event loop...")
        exit_code = app.exec()
        logger.info(f"Qt event loop exited with code: {exit_code}")
        return exit_code

    except Exception as exc:
        logger.critical(f"Fatal application error: {exc}", exc_info=True)
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Application interrupted by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal application error: {e}", exc_info=True)
        sys.exit(1)

