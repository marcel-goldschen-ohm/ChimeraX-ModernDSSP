# vim: set expandtab shiftwidth=4 softtabstop=4:

# === UCSF ChimeraX Copyright ===
# Copyright 2016 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  For details see:
# https://www.rbvi.ucsf.edu/chimerax/docs/licensing.html
# This notice must be embedded in or attached to all copies,
# including partial copies, of the software or any revisions
# or derivations thereof.
# === UCSF ChimeraX Copyright ===

from chimerax.core.tools import ToolInstance
from Qt.QtCore import QThread, Signal


class SecondaryStructureTool(ToolInstance):

    # Inheriting from ToolInstance makes us known to the ChimeraX tool mangager,
    # so we can be notified and take appropriate action when sessions are closed,
    # saved, or restored, and we will be listed among running tools and so on.
    #
    # If cleaning up is needed on finish, override the 'delete' method
    # but be sure to call 'delete' from the superclass at the end.

    SESSION_ENDURING = False    # Does this instance persist when session closes
    SESSION_SAVE = False         # We do save/restore in sessions
    # help = "help:user/tools/SecondaryStructure.html" # Let ChimeraX know about our help page

    def __init__(self, session, tool_name):
        # 'session'   - chimerax.core.session.Session instance
        # 'tool_name' - string

        # Initialize base class.
        super().__init__(session, tool_name)

        # Set name displayed on title bar (defaults to tool_name)
        # Must be after the superclass init, which would override it.
        self.display_name = "Secondary Structure"

        # Create the main window for our tool.  The window object will have
        # a 'ui_area' where we place the widgets composing our interface.
        # The window isn't shown until we call its 'manage' method.
        #
        # Note that by default, tool windows are only hidden rather than
        # destroyed when the user clicks the window's close button.  To change
        # this behavior, specify 'close_destroys=True' in the MainToolWindow
        # constructor.
        from chimerax.ui import MainToolWindow
        self.tool_window = MainToolWindow(self)

        # The path to the DSSP executable. Can be changed in the settings dialog.
        self.dssp_executable_path = "/opt/homebrew/bin/mkdssp"

        # RGBA color scheme for the DSSP secondary structure. Can be changed in the settings dialog.
        self.default_dssp_schema = {
            "H": {"description": "alpha helix", "color": (255, 0, 0, 255)},
            "G": {"description": "3-10 helix", "color": (255, 255, 0, 255)},
            "I": {"description": "pi helix", "color": (255, 165, 0, 255)},
            "P": {"description": "poly-proline II helix", "color": (255, 138, 216, 255)},
            "E": {"description": "extended beta strand", "color": (0, 0, 255, 255)},
            "B": {"description": "beta bridge", "color": (0, 255, 0, 255)},
            "T": {"description": "hydrogen-bonded turn", "color": (128, 0, 128, 255)},
            "S": {"description": "bend", "color": (0, 255, 255, 255)},
            "C": {"description": "coil or unassigned", "color": (255, 255, 255, 255)},
        }
        from copy import deepcopy
        self.dssp_schema = deepcopy(self.default_dssp_schema)

        # We will store the DSSP output data for each model in a list of dictionaries.
        self.dssp_data = []

        # We will be adding an item to the tool's context menu, so override
        # the default MainToolWindow fill_context_menu method
        # self.tool_window.fill_context_menu = self.fill_context_menu

        # Our user interface is simple enough that we could probably inline
        # the code right here, but for any kind of even moderately complex
        # interface, it is probably better to put the code in a method so
        # that this __init__ method remains readable.
        self._build_ui()

    def _build_ui(self):
        # Put our widgets in the tool window
        from Qt.QtWidgets import QPushButton, QGridLayout

        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_dssp)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_dssp)
        
        self.color_ribbons_button = QPushButton("Color Ribbons")
        self.color_ribbons_button.clicked.connect(self.color_ribbons)
        
        self.color_atoms_button = QPushButton("Color Atoms")
        self.color_atoms_button.clicked.connect(self.color_atoms)
        
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.settings)
        
        self.help_button = QPushButton("Help")
        self.help_button.clicked.connect(self.show_help)

        layout = QGridLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        layout.addWidget(self.run_button, 0, 0)
        layout.addWidget(self.clear_button, 1, 0)
        layout.addWidget(self.color_ribbons_button, 0, 1)
        layout.addWidget(self.color_atoms_button, 1, 1)
        layout.addWidget(self.settings_button, 0, 2)
        layout.addWidget(self.help_button, 1, 2)

        # Set the layout as the contents of our window
        self.tool_window.ui_area.setLayout(layout)

        # Show the window on the user-preferred side of the ChimeraX
        # main window
        self.tool_window.manage('side')

    def get_model_by_id(self, model_id):
        for model in self.session.models.list():
            if model.id == model_id:
                return model
        return None

    def get_dssp_data_for_model_id(self, model_id):
        for data in self.dssp_data:
            if data['model_id'] == model_id:
                return data
        return None

    def is_protein_model(self, model):
        from chimerax.atomic import AtomicStructure

        # Check if the model is an atomic structure (excludes density maps, surfaces, etc.)
        if not isinstance(model, AtomicStructure):
            return False
            
        # Get all residues in the model
        residues = model.residues
        if len(residues) == 0:
            return False
            
        # Check if any residue is typed as a peptide/amino acid polymer
        # 1 = PT_AMINO_ACID (standard protein/peptide residue)
        return any(r.polymer_type == 1 for r in residues)

    def clear_dssp(self):
        for data in self.dssp_data:
            self._cleanup_temp_files(data)
        self.dssp_data = []
    
    def run_dssp(self):
        self.session.logger.status(f"\nRunning DSSP at {self.dssp_executable_path} ...", log=True)

        # Keep trach of worker threads for running DSSP in the background. This is important to avoid blocking the GUI.
        self.worker_count = 0

        models = []
        for model in self.session.models.list():
            if not (model.selected or model.visible):
                continue
            existing_data = self.get_dssp_data_for_model_id(model.id)
            if existing_data:
                continue
            if not self.is_protein_model(model):
                # self.session.logger.warning(f"Model {model.name} is not a protein model. Skipping DSSP.")
                continue
            models.append(model)

        if not models:
            self.session.logger.status("No new protein models selected for DSSP.", log=True)
            self.session.logger.info("No new protein models selected for DSSP. DSSP runs only on models that are visible or selected and for which DSSP data is not already available.")
            return

        for model in models:
            self.start_dssp(model)

    def start_dssp(self, model):
        import tempfile
        import shlex
        from chimerax.pdb import save_pdb

        self.session.logger.info(f"... DSSP started for {model.name} ...")

        # Prepare a dictionary to hold the DSSP data for this model
        data = {
            'model_id': model.id,
            'input_file': None,
            'output_file': None,
            'dssp': None,
            'chain_ids': None,
            'residue_numbers': None,
            'secondary_structures': None,
            'selections': None,
        }

        # Create temporary input and output files
        # These files will persist until we explicitly delete them, which we will do after processing the DSSP output
        with tempfile.NamedTemporaryFile(mode='w+t', encoding='utf-8', suffix=".pdb", delete=False) as input_file:
            data['input_file'] = input_file.name
            save_pdb(self.session, data['input_file'], models=[model])

        with tempfile.NamedTemporaryFile(mode='w+t', encoding='utf-8', delete=False) as output_file:
            data['output_file'] = output_file.name

        # Construct the command to run DSSP
        data['command'] = f"{self.dssp_executable_path} --output-format dssp {data['input_file']} {data['output_file']}"
        
        # Add the data dictionary to the list of DSSP data for tracking
        self.dssp_data.append(data)

        cmd_list = shlex.split(data['command'])
        
        # Start the DSSP process in a separate thread to avoid blocking the GUI
        self.worker_count += 1
        self.worker = AppWorkerThread(cmd_list)
        # self.worker.output_received.connect(self.handle_live_log)
        self.worker.finished_successfully.connect(lambda data=data: self._finish_dssp(data))
        self.worker.failed.connect(lambda error_message, data=data: self._handle_dssp_error(data, error_message))
        self.worker.start()

    def _finish_dssp(self, data):
        self.worker_count -= 1

        model = self.get_model_by_id(data['model_id'])
        self.session.logger.info(f"... DSSP completed for {model.name}")

        # Read the DSSP output from the temporary output file
        with open(data['output_file'], 'r') as f:
            data['dssp'] = f.read()

        # Parse the DSSP output to extract chain IDs, residue numbers, and secondary structures
        self._parse_dssp_output(data)

        # Log the DSSP output for the model
        # self.log_dssp_output(data)

        # Delete the temporary input and output files to clean up
        self._cleanup_temp_files(data)

        if self.worker_count == 0:
            self.session.logger.status("Finished running DSSP.\n", log=True)

    def _handle_dssp_error(self, data, error_message):
        self.worker_count -= 1

        model = self.get_model_by_id(data['model_id'])
        self.session.logger.warning(f"... ERROR: DSSP failed for {model.name}: {error_message}")

        # Delete the temporary input and output files to clean up
        self._cleanup_temp_files(data)

        if self.worker_count == 0:
            self.session.logger.status("Finished running DSSP.\n", log=True)

    def _clean_dssp(self, data):
        self._cleanup_temp_files(data)
        self.dssp_data.remove(data)

    def _cleanup_temp_files(self, data):
        import os
        temp_file = data.get('input_file', None)
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
            data['input_file'] = None
        temp_file = data.get('output_file', None)
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
            data['output_file'] = None

    def _log_dssp_output(self, data):
        model = self.get_model_by_id(data['model_id'])
        self.session.logger.info(f"DSSP Output for {model.name}:")
        for chain_id, residue_number, secondary_structure in zip(data['chain_ids'], data['residue_numbers'], data['secondary_structures']):
            self.session.logger.info(f"{chain_id} {residue_number:>6} {secondary_structure}")

    def _parse_dssp_output(self, data):
        import numpy as np
        chain_ids = []
        residue_numbers = []
        secondary_structures = []
        lines = data['dssp'].splitlines()
        header = True
        for line in lines:
            if line.startswith("  #  RESIDUE"):
                header = False
                continue
            if header:
                continue
            residue_number = line[5:10].strip()
            chain_id = line[11].strip()
            if not residue_number or not chain_id:
                continue
            secondary_structure = line[16].strip()
            chain_ids.append(chain_id)
            residue_numbers.append(residue_number)
            secondary_structures.append(secondary_structure)
        data['chain_ids'] = np.array(chain_ids)
        data['residue_numbers'] = np.array(residue_numbers).astype(int)
        data['secondary_structures'] = np.array(secondary_structures)

        # from chimerax.atomic import Residues, Atoms
        model_id = data['model_id']
        model = self.get_model_by_id(model_id)
        residues = model.residues
        selections = {}
        for key in self.dssp_schema:
            mask = data['secondary_structures'] == key
            if not np.any(mask):
                continue
            selected_chain_ids = data['chain_ids'][mask]
            selected_residue_numbers = data['residue_numbers'][mask]
            mask = np.zeros(len(residues), dtype=bool)
            for chain_id in np.unique(selected_chain_ids):
                chain_residue_numbers = selected_residue_numbers[selected_chain_ids == chain_id]
                chain_mask = (residues.chain_ids == chain_id) & np.isin(residues.numbers, chain_residue_numbers)
                mask |= chain_mask
            selected_residues = residues[mask]
            atoms = selected_residues.atoms
            selections[key] = {
                'residues': selected_residues,
                'atoms': atoms
            }
            for atom in atoms:
                # custom attribute for easy use in scripts and commands
                atom.dssp = key
                # custom properties are discoverable to ChimeraX tools and inspectors
                if not hasattr(atom, 'custom_properties'):
                    atom.custom_properties = {}
                atom.custom_properties['dssp'] = key
        data['selections'] = selections

    def color_ribbons(self):
        if not self.dssp_data:
            self.session.logger.warning("No DSSP data available. Please run DSSP first.")
            return
        for data in self.dssp_data:
            model_id = data['model_id']
            model = self.get_model_by_id(model_id)
            if not (model.selected or model.visible):
                continue
            for key, selection in data['selections'].items():
                color = self.dssp_schema[key]["color"]
                for residue in selection['residues']:
                    residue.ribbon_color = color

    def color_atoms(self):
        if not self.dssp_data:
            self.session.logger.warning("No DSSP data available. Please run DSSP first.")
            return
        for data in self.dssp_data:
            model_id = data['model_id']
            model = self.get_model_by_id(model_id)
            if not (model.selected or model.visible):
                continue
            for key, selection in data['selections'].items():
                color = self.dssp_schema[key]["color"]
                selection['atoms'].colors = [color] * len(selection['atoms'])

    def settings(self):
        from Qt.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QToolButton, QPushButton, QDialogButtonBox

        dialog = QDialog()
        dialog.setWindowTitle("Modern DSSP Settings")
        layout = QFormLayout(dialog)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        info_label = QLabel("Requires installation of DSSP. For example, on macOS you can install it with Homebrew: `brew install brewsci/bio/dssp`, in which case the executable may be located at `/opt/homebrew/bin/mkdssp`.")
        info_label.setWordWrap(True)
        layout.addRow(info_label)

        dssp_path = QLineEdit()
        dssp_path.setText(self.dssp_executable_path)
        dssp_path.setPlaceholderText("Path to your DSSP executable (e.g., /usr/bin/mkdssp)")
        layout.addRow("DSSP path:", dssp_path)

        self.color_buttons = {}
        for key in self.dssp_schema:
            description = self.dssp_schema[key]["description"]
            color = self.dssp_schema[key]["color"]
            button = QToolButton()
            button.setStyleSheet(f"background-color: rgba{color};")
            button.clicked.connect(lambda _, k=key: self._pick_color(k))
            self.color_buttons[key] = button
            layout.addRow(f"{description} ({key})", button)

        default_colors_button = QPushButton("Default Colors")
        default_colors_button.clicked.connect(self.default_colors)
        layout.addRow(default_colors_button)

        buttons = QDialogButtonBox(dialog)
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() != QDialog.Accepted:
            self.color_buttons = {}
            return

        self.dssp_executable_path = dssp_path.text().strip()

        for key, button in self.color_buttons.items():
            color = button.palette().button().color()
            self.dssp_schema[key]["color"] = (color.red(), color.green(), color.blue(), color.alpha())

        self.color_buttons = {}

    def _pick_color(self, key):
        from Qt.QtGui import QColor
        from Qt.QtWidgets import QColorDialog
        description = self.dssp_schema[key]["description"]
        initial_color = QColor(*self.dssp_schema[key]["color"])
        color = QColorDialog.getColor(initial=initial_color, title=f"Select color for {description}: {key}", options=QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            color_tuple = (color.red(), color.green(), color.blue(), color.alpha())
            self.dssp_schema[key]["color"] = color_tuple
            try:
                self.color_buttons[key].setStyleSheet(f"background-color: rgba{color_tuple};")
            except:
                pass

    def default_colors(self):
        from copy import deepcopy
        self.dssp_schema = deepcopy(self.default_dssp_schema)
        for key, button in self.color_buttons.items():
            color = self.dssp_schema[key]["color"]
            button.setStyleSheet(f"background-color: rgba{color};")
        self.session.logger.info("DSSP colors reset to default.")

    def show_help(self):
        from Qt.QtWidgets import QMessageBox

        title = "Secondary Structure Tool Help"
        text = "For help with the Secondary Structure Tool, please refer to the plugin repository at: https://github.com/marcel-goldschen-ohm/ChimeraX-SecondaryStructure"

        QMessageBox.information(None, title, text)


class AppWorkerThread(QThread):
    # Define custom Qt signals to safely update the GUI from a background thread
    # output_received = Signal(str)
    finished_successfully = Signal()
    failed = Signal(str)

    def __init__(self, command_list):
        super().__init__()
        self.command_list = command_list

    def run(self):
        try:
            import subprocess
            # Start the process tracking stdout line-by-line
            process = subprocess.Popen(
                self.command_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # full_output = []
            # # Read stdout line by line as it is generated by the OS application
            # for line in process.stdout:
            #     full_output.append(line)
            #     # self.output_received.emit(line.strip()) # Send line to UI (e.g., for a progress log)
                
            process.wait() # Wait for final exit status
            
            if process.returncode == 0:
                # self.finished_successfully.emit("".join(full_output))
                self.finished_successfully.emit()
            else:
                stderr_text = process.stderr.read()
                self.failed.emit(f"Process exited with code {process.returncode}. Error: {stderr_text}")
                
        except Exception as e:
            self.failed.emit(str(e))
