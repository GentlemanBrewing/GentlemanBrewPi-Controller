import sqlite3

conn = sqlite3.connect('Log.db')

c = conn.cursor()

# Create table
c.execute('''CREATE TABLE PIDOutput(DateTime, ProcessName, Temperature, Duty, Setpoint, SafetyTemp, SafetyTrigger, Status)''')

# Save (commit) the changes
conn.commit()

# We can also close the connection if we are done with it.
# Just be sure any changes have been committed or they will be lost.
conn.close()