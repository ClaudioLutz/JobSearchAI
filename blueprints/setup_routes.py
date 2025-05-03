import logging # Import logging module
from flask import Blueprint, render_template, request, redirect, url_for, flash
from config import config # Import the updated config instance
import os
from pathlib import Path
# Import necessary libraries for API key validation (if needed)
# from openai import OpenAI, AuthenticationError

# Set up logger for this blueprint
logger = logging.getLogger(__name__)

setup_bp = Blueprint('setup', __name__, url_prefix='/setup')

# --- Helper Function (Example: Basic OpenAI Key Validation) ---
# Note: A real validation might involve a simple, low-cost API call.
# Be mindful of rate limits and costs associated with validation calls.
def validate_openai_key(api_key: str) -> bool:
    """Placeholder for validating the OpenAI API key format or via a test call."""
    if not api_key:
        return False
    # Basic format check (starts with 'sk-' and has expected length)
    if not api_key.startswith("sk-") or len(api_key) < 40:
         logger.warning("API Key format seems invalid.")
         # return False # Optionally enforce format check

    # Example using a minimal API call (uncomment and adapt if needed):
    # try:
    #     client = OpenAI(api_key=api_key)
    #     client.models.list(limit=1) # Make a cheap API call
    #     logger.info("OpenAI API key validated successfully.")
    #     return True
    # except AuthenticationError:
    #     logger.error("OpenAI API key validation failed: Authentication Error.")
    #     return False
    # except Exception as e:
    #     logger.error(f"Error during OpenAI API key validation: {e}")
    #     return False # Or True if you want to allow potentially valid keys despite validation error

    # For now, just check if it's not empty after basic checks
    return True


# --- Setup Wizard Route ---
@setup_bp.route('/', methods=['GET', 'POST'])
def setup_wizard():
    # Prevent access if setup is already complete
    if not config.is_first_run():
        flash('Setup has already been completed.', 'info')
        return redirect(url_for('index')) # Redirect to main dashboard

    if request.method == 'POST':
        openai_api_key = request.form.get('openai_api_key', '').strip()
        data_dir_input = request.form.get('data_dir', '').strip()

        # --- Validate API Key ---
        if not openai_api_key:
            flash('OpenAI API key is required.', 'error')
            return render_template('setup_wizard.html', data_dir=data_dir_input) # Keep user input

        if not validate_openai_key(openai_api_key):
             flash('The provided OpenAI API key appears invalid. Please check and try again.', 'error')
             return render_template('setup_wizard.html', data_dir=data_dir_input) # Keep user input

        # --- Store API Key ---
        if not config.set_api_key('openai', openai_api_key):
             flash('Failed to store the API key securely. Please check permissions or try again.', 'error')
             return render_template('setup_wizard.html', data_dir=data_dir_input) # Keep user input

        # --- Handle Data Directory ---
        data_dir_path = None
        if data_dir_input:
            # User provided a custom path
            try:
                data_dir_path = Path(data_dir_input).resolve()
                # Basic validation: check if it's a directory or can be created
                if not data_dir_path.is_dir():
                    data_dir_path.mkdir(parents=True, exist_ok=True) # Try creating it
                config.USER_SETTINGS['custom_data_dir'] = str(data_dir_path)
                logger.info(f"Set custom data directory: {data_dir_path}")
            except Exception as e:
                flash(f'Invalid custom data directory path: {e}', 'error')
                return render_template('setup_wizard.html', data_dir=data_dir_input)
        else:
            # Use default user data directory
            data_dir_path = config.USER_DATA_DIR
            if 'custom_data_dir' in config.USER_SETTINGS:
                 del config.USER_SETTINGS['custom_data_dir'] # Remove custom setting if user clears the field
            logger.info(f"Using default data directory: {data_dir_path}")

        # --- Create Necessary Subdirectories in the chosen data_dir ---
        try:
            subdirs = [
                "process_cv/cv-data/input",
                "process_cv/cv-data/processed",
                "process_cv/cv-data/html",
                "job-data-acquisition/data",
                "job_matches",
                "motivation_letters",
                "logs"
            ]
            for sub in subdirs:
                (data_dir_path / sub).mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured necessary subdirectories exist in {data_dir_path}")
        except Exception as e:
             flash(f'Error creating subdirectories in data directory: {e}', 'error')
             # Don't necessarily fail setup, but log the error
             logger.error(f"Failed to create subdirectories in {data_dir_path}: {e}")


        # --- Mark Setup as Complete & Save ---
        config.USER_SETTINGS['setup_complete'] = True
        if config.save_user_settings():
            flash('Setup completed successfully!', 'success')
            # Re-initialize config to pick up custom data dir immediately if set
            config.__init__() # Force re-initialization
            return redirect(url_for('index'))
        else:
            flash('Setup completed, but failed to save settings permanently.', 'warning')
            return redirect(url_for('index')) # Proceed anyway, but warn user

    # GET request: Show the setup form
    default_data_dir = str(config.USER_DATA_DIR)
    return render_template('setup_wizard.html', data_dir=default_data_dir)


# --- Configuration Update Routes (to be added later) ---

@setup_bp.route('/update_api_key', methods=['POST'])
def update_api_key():
    # Prevent access if setup is not complete
    if config.is_first_run():
        flash('Please complete the initial setup first.', 'warning')
        return redirect(url_for('setup.setup_wizard'))

    openai_api_key = request.form.get('openai_api_key', '').strip()
    if openai_api_key:
        if not validate_openai_key(openai_api_key):
             flash('The provided OpenAI API key appears invalid. Please check and try again.', 'error')
        elif config.set_api_key('openai', openai_api_key):
            flash('API key updated successfully.', 'success')
        else:
            flash('Failed to update API key securely.', 'error')
    else:
        flash('No new API key provided.', 'info')
    return redirect(url_for('index', _anchor='configuration')) # Redirect back to config tab

@setup_bp.route('/update_data_dir', methods=['POST'])
def update_data_dir():
     # Prevent access if setup is not complete
    if config.is_first_run():
        flash('Please complete the initial setup first.', 'warning')
        return redirect(url_for('setup.setup_wizard'))

    use_default = 'use_default' in request.form
    data_dir_input = request.form.get('data_dir', '').strip()
    settings_changed = False

    if use_default:
        if 'custom_data_dir' in config.USER_SETTINGS:
            del config.USER_SETTINGS['custom_data_dir']
            settings_changed = True
            flash('Data directory reset to default. Restart the application for changes to take full effect.', 'success')
        else:
             flash('Already using the default data directory.', 'info')
    elif data_dir_input:
        try:
            new_data_dir = str(Path(data_dir_input).resolve())
            if config.USER_SETTINGS.get('custom_data_dir') != new_data_dir:
                 # Basic validation: check if it's a directory or can be created
                path_obj = Path(new_data_dir)
                if not path_obj.is_dir():
                    path_obj.mkdir(parents=True, exist_ok=True) # Try creating it

                config.USER_SETTINGS['custom_data_dir'] = new_data_dir
                settings_changed = True
                flash('Data directory updated. Restart the application for changes to take full effect.', 'success')
            else:
                 flash('Data directory is already set to this path.', 'info')
        except Exception as e:
            flash(f'Invalid custom data directory path: {e}', 'error')
            return redirect(url_for('index', _anchor='configuration'))
    else:
         flash('No data directory specified.', 'warning')


    if settings_changed:
        if not config.save_user_settings():
             flash('Failed to save the new data directory setting.', 'error')
        else:
             # Optionally trigger re-initialization or prompt restart
             pass

    return redirect(url_for('index', _anchor='configuration')) # Redirect back to config tab
