import sys
from guidata.qthelpers import qt_app_context
from guidata.configtools import get_icon
from guidata.dataset.datatypes import DataSet
from guidata.dataset.dataitems import StringItem
from guidata.dataset.qtwidgets import DataSetEditDialog
from qtpy.QtWidgets import QMessageBox, QApplication
from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon

class WarningDialog:
    """A reusable warning dialog class for displaying dynamic messages"""
    
    @staticmethod
    def show_warning(message, title="Warning", parent=None):
        """
        Display a warning dialog with a dynamic message
        
        Args:
            message (str): The warning message to display
            title (str): The dialog title (default: "Warning")
            parent: Parent widget (optional)
            
        Returns:
            QMessageBox.StandardButton: The button clicked by user
        """
        # Create message box
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setDefaultButton(QMessageBox.Ok)
        
        # Try to set warning icon if available
        try:
            warning_icon = get_icon('warning.png')
            if warning_icon:
                msg_box.setWindowIcon(warning_icon)
        except:
            pass  # Icon not available, continue without it
        
        return msg_box.exec_()

    @staticmethod
    def show_warning_with_options(message, title="Warning", buttons=None, parent=None):
        """
        Display a warning dialog with custom button options
        
        Args:
            message (str): The warning message to display
            title (str): The dialog title
            buttons (list): List of button types (default: [QMessageBox.Ok, QMessageBox.Cancel])
            parent: Parent widget (optional)
            
        Returns:
            QMessageBox.StandardButton: The button clicked by user
        """
        if buttons is None:
            buttons = [QMessageBox.Ok, QMessageBox.Cancel]
        
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        # Add buttons
        standard_buttons = QMessageBox.NoButton
        for button in buttons:
            standard_buttons |= button
        
        msg_box.setStandardButtons(standard_buttons)
        msg_box.setDefaultButton(buttons[0])
        
        return msg_box.exec_()

class WarningDataSet(DataSet):
    """Alternative approach using DataSet for more complex warning dialogs"""
    message = StringItem("Warning Message", default="")

def show_dataset_warning(message, title="Warning"):
    """
    Show warning using DataSet approach (for more complex scenarios)
    
    Args:
        message (str): The warning message
        title (str): Dialog title
    """
    warning_data = WarningDataSet()
    warning_data.message = message
    
    dialog = DataSetEditDialog(warning_data, title=title, icon=get_icon('warning.png'))
    dialog.setReadOnly(True)  # Make it read-only since it's just a warning
    return dialog.exec_()

# Example usage functions
def example_basic_warning():
    """Example of basic warning dialog usage"""
    message = "This is a dynamic warning message!"
    result = WarningDialog.show_warning(message, "System Warning")
    print(f"User clicked: {result}")

def example_warning_with_options():
    """Example of warning dialog with custom buttons"""
    message = "Are you sure you want to delete this file?\nThis action cannot be undone."
    buttons = [QMessageBox.Yes, QMessageBox.No, QMessageBox.Cancel]
    
    result = WarningDialog.show_warning_with_options(
        message, 
        "Confirm Deletion", 
        buttons
    )
    
    if result == QMessageBox.Yes:
        print("User confirmed deletion")
    elif result == QMessageBox.No:
        print("User declined deletion")
    else:
        print("User cancelled")

def example_conditional_warnings():
    """Example showing how to use dynamic messages based on conditions"""
    
    # Simulate different error conditions
    error_conditions = {
        'file_not_found': "The specified file could not be found.",
        'permission_denied': "You don't have permission to access this resource.",
        'network_error': "Network connection failed. Please check your internet connection.",
        'invalid_input': "The input data is invalid. Please check your entries.",
    }
    
    # Simulate triggering different warnings
    for condition, message in error_conditions.items():
        print(f"Triggering warning for: {condition}")
        WarningDialog.show_warning(
            message, 
            f"Error: {condition.replace('_', ' ').title()}"
        )

# Utility function for easy import and use
def myGUIDATAwarn(message, title="Warning", buttons=None):
    """
    Convenience function for quick warning dialogs
    
    Args:
        message (str): Warning message
        title (str): Dialog title
        buttons (list): Optional button list
        
    Returns:
        Button result
    """
    if buttons:
        return WarningDialog.show_warning_with_options(message, title, buttons)
    else:
        return WarningDialog.show_warning(message, title)

# Main execution
if __name__ == "__main__":
    # Create Qt application context
    with qt_app_context(exec_loop=True):
        # Example usage
        print("Showing basic warning...")
        example_basic_warning()
        
        print("Showing warning with options...")
        example_warning_with_options()
        
        print("Showing conditional warnings...")
        # Uncomment the next line to see multiple warnings
        # example_conditional_warnings()

