import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkcalendar import DateEntry
import datetime
import pytz
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']

# Function to handle form submission
def execute_script():
    media_name = media_var.get()
    start_date = cal_start.get()
    end_date = cal_end.get()
    # test
    # flow = InstalledAppFlow.from_client_secrets_file('client_secret.json',SCOPES)
    
    # # Authenticate using the credentials.json
    # creds = flow.run_local_server(port=0)

    # # Authorize the client
    # client = gspread.authorize(creds)

    # # Open the Google Spreadsheet (replace 'spreadsheet_name' with the actual name)
    # # spreadsheet = client.open('Instagramインサイトデータ更新')
    # spreadsheet = client.open('test_instagram')

    # Select a specific sheet by its name (or use .sheet1 for the first sheet)
    
    ##
    if media_name and start_date and end_date:
        # Here you can call your Python function with the selected parameters
        messagebox.showinfo("Success", f"Media: {media_name}\nStart Date: {start_date}\nEnd Date: {end_date}")
        
        # sheet = spreadsheet.worksheet(media_name)
        # header = ['param1','param2']
        # sheet.insert_row(header, 1)
        # Call your actual Python script logic here using these parameters
        # Example:
        # my_python_script(media_name, start_date, end_date)
    else:
        messagebox.showerror("Error", "Please fill out all fields.")

# Create main window
root = tk.Tk()
root.title("Media Script Runner")

# Create dropdown for media name
media_var = tk.StringVar()
media_label = tk.Label(root, text="Select Media Name")
media_label.grid(row=0, column=0, padx=10, pady=10)

media_options = ["hodinkee", "ELLE JAPAN", "ELLE beauty"]  # Add your media options here
media_dropdown = ttk.OptionMenu(root, media_var, media_options[0], *media_options)
media_dropdown.grid(row=0, column=1, padx=10, pady=10)

# Create date pickers for start and end date
start_label = tk.Label(root, text="Select Start Date")
start_label.grid(row=1, column=0, padx=10, pady=10)
cal_start = DateEntry(root, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
cal_start.grid(row=1, column=1, padx=10, pady=10)

end_label = tk.Label(root, text="Select End Date")
end_label.grid(row=2, column=0, padx=10, pady=10)
cal_end = DateEntry(root, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
cal_end.grid(row=2, column=1, padx=10, pady=10)

# Create execute button
execute_button = tk.Button(root, text="Execute", command=execute_script)
execute_button.grid(row=3, columnspan=2, pady=20)

# Start the GUI loop
root.mainloop()