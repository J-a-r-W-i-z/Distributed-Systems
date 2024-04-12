import os

path = os.getcwd()
print("path:", path)
os.system("ls")

# create a new directory called wal if not exists in the current path
if not os.path.exists(f"{path}/wal"):
    os.makedirs(f"{path}/wal")
