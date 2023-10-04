'''
main module of a user administration for the BEGö nextcloud 

Created on 7.9.2023

@author: Ulrich Schwardmann
licence: CC BY-SA 
'''

import sys
import os
import argparse
import json
import csv
import ssl
import string
import secrets
import datetime
import smtplib
import base64
import codecs
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from nextcloud import NextCloud

############ global parameters #############        

BEGOE_CREDS = "/tmp/Certs/otherCredentials/"
BEGOE_DIR = "/home/uschwar1/Dokumente/begoe_nextcloud/"
BEGOE_ADMIN = "begadmin"
BEGOE_MAILACCT = "WebDe_ulrich"
#BEGOE_MAILACCT = "begoe_teamadmin"
BEGOE_ADMIN_CRED = BEGOE_CREDS + "nextcloud_" + BEGOE_ADMIN + ".txt"
BEGOE_MAILACCT_CRED = BEGOE_CREDS + "mail_" + BEGOE_MAILACCT + ".txt"
USER_INPUT_CSV_FILE = BEGOE_DIR + 'user_inputfile.csv'
USER_CSV_FILE = BEGOE_DIR + 'user_file.csv'
USER_WELCOME_FILE = BEGOE_DIR + 'user_welcome.txt'
USER_FAREWELL_FILE = BEGOE_DIR + 'user_farewell.txt'
BEGOE_LOGO_FILE =  BEGOE_DIR + '/pictures/BEG_Logo_weiss.webp'

PASSWORD_LG = 10
SEND_USER_MSG = True

#########################        

class Mailing():

    def __init__(self,relay=True):
        self.relay = relay
        try:
            self.credfile = open(BEGOE_MAILACCT_CRED,"r")
        except:
            print("Error: credential file not found! at " + BEGOE_MAILACCT_CREDS)
            sys.exit(1)
        self.credstr = self.credfile.read()
        self.cred = json.loads(self.credstr)
        MAIL_SERVER_PORT = self.cred['baseuri'].split(":")
        self.MAIL_SERVER = MAIL_SERVER_PORT[0]
        if len(MAIL_SERVER_PORT) == 2:
            self.MAIL_PORT = int(MAIL_SERVER_PORT[1])
        else:
            self.MAIL_PORT = 587
        self.MAIL_USERNAME = self.cred['username']
        self.MAIL_PASSWORD = self.cred['password']            
    
    def text2ascii(self,utf8text):
        text = ''
        for zeichen in utf8text:
            if zeichen=='ä':
               text = text + 'ae'
            elif zeichen=='ö':
               text = text + 'oe'
            elif zeichen=='ü':
               text = text + 'ue'
            elif zeichen=='Ä':
               text = text + 'Ae'
            elif zeichen=='Ö':
               text = text + 'Oe'
            elif zeichen=='Ü':
               text = text + 'Ue'
            elif zeichen=='ß':
               text = text + 'ss'
            else:
               text = text + zeichen
        return text
    
    def text2html(self,utf8text):
        text = ''
        for zeichen in utf8text:
            if zeichen=='ä':
               text = text + '&auml;'
            elif zeichen=='ö':
               text = text + '&ouml;'
            elif zeichen=='ü':
               text = text + '&uuml;'
            elif zeichen=='Ä':
               text = text + '&Auml;'
            elif zeichen=='Ö':
               text = text + '&Ouml;'
            elif zeichen=='Ü':
               text = text + '&Uuml;'
            elif zeichen=='ß':
               text = text + '&szlig;'
            elif zeichen=='\n':
                text = text + '\n<br>'
            else:
               text = text + zeichen
        return text
    
    
    def mail_message(self,userid,user_email,subject,prefix,infile):
        text = prefix
        # with open(USER_FAREWELL_FILE) as file:
        #     for line in file:
        #         text += line
        text += open(infile, 'r').read() # codecs.open(USER_FAREWELL_FILE, 'r', 'utf-8').read()
        text += "\n\n"
        text_ascii = self.text2ascii(text)
        text_html = self.text2html(text)
        img_name = BEGOE_LOGO_FILE.split("/")[-1].split(".")[0]
        text_html += "<br><img src='cid:" + img_name + "'>"
        self.sendmail(self.MAIL_USERNAME, [user_email], subject, text_ascii, text_html, attachments=[BEGOE_LOGO_FILE],img_names=[img_name])
    
    
    def sendmail(self, sender, receivers, subject, text_plain, text_html, attachments=None, img_names=[]):
        # Create the root message and fill in the from, to, and subject headers
        msgRoot = MIMEMultipart('related')
        msgRoot['Subject'] = subject
        msgRoot['From'] = sender
        msgRoot['To'] = ', '.join(receivers)
        msgRoot.preamble = text_plain
        
        # Encapsulate the plain and HTML versions of the message body in an
        # 'alternative' part, so message agents can decide which they want to display.
        msgAlternative = MIMEMultipart('alternative')
        msgRoot.attach(msgAlternative)
        
        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        msgText1 = MIMEText(text_plain.encode('utf8').decode('us-ascii'), 'plain')
        msgText2 = MIMEText(text_html, 'html')
        msgAlternative.attach(msgText1)
        msgAlternative.attach(msgText2)
    
        if attachments != None:
            i = 0
            for file in attachments:
                # Open the files in binary mode.  Let the MIMEImage class 
                # automatically guess the specific attachment type.
                with open(file, 'rb') as fp:
                    att = MIMEImage(fp.read())
                    att.add_header('Content-ID', img_names[i])
                    att.add_header('Content-Disposition',  'attachment')
                msgRoot.attach(att)
                i += 1
        
        # Send the message via local SMTP server. 
        if self.relay: # Assume mail relay
            smtp = smtplib.SMTP('localhost')
            smtp.sendmail(sender, receivers, msgRoot.as_string())
            smtp.quit()
        else: # use direct user access 
            context=ssl.create_default_context()
            with smtplib.SMTP(self.MAIL_SERVER, port=self.MAIL_PORT) as smtp:
                smtp.starttls(context=context)
                smtp.login(self.MAIL_USERNAME, self.MAIL_PASSWORD)
                smtp.sendmail(sender, receivers, msgRoot.as_string())
                print ("email sent to: " + msgRoot['To'])
                # smtp.send_message(msgRoot.as_string())



#########################        
class Local_User_DB():

    def __init__(self,NXC):
        self.NXC = NXC
        self.users = self.get_existing_users_from_csv()
        self.time_now = self.get_timenow()
        if not self.local_csv_in_sync_with_nxc():
            print ("Warning: local csv not in sync with nextcloud users, consider synchronization of csv with nextcloud")
        self.nxc_users = {}
            
    def get_existing_users_from_csv(self):
        local_users = []
        userDict = {}
        try:
            with open(USER_CSV_FILE) as csv_file:
                reader = csv.DictReader(csv_file, delimiter=';')
                for row in reader:
                    local_users.append(row)
                    try:
                        userDict[row["Userid"]] = row
                    except:
                        print ("Error: no Userid in: " + str(row))
        except FileNotFoundError:
            print ("Error: No such file or directory: " + USER_CSV_FILE)
            sys.exit(1)
        print (json.dumps(userDict, sort_keys=True,indent=2, separators=(',', ' : ')))
        return userDict

    def get_missing_nextcloud_userids(self):
        missing_userids = []
        for item in self.NXC.users_exist:
            try:
                self.users[item]
            except:
                missing_userids.append(item)
                print ("Warning: userid " + item + " not found in local user DB")
        # for item in self.users:
        #     if item not in NXC.users_exist:
        #         same_userids = False
        #         print ("Warning: userid " + item + "not found in local user DB")
        return missing_userids

    def local_csv_in_sync_with_nxc(self):
        in_sync = True
        for item in self.NXC.users_exist:
            try:
                self.users[item]
            except:
                in_sync = False
                print ("Warning: nxc userid " + item + " not found in local user DB")
        for item in self.users:
            if item not in self.NXC.users_exist:
                in_sync = False
                print ("Warning: local userid " + item + " not found in nxc DB")
        return in_sync

    def update_with_nextcloud_userids(self, userids):
        nxc_users = {}
        if userids == None:
            userids = self.NXC.users_exist
        for userid in userids:
            if verbosity > 1:
                print("from NXC get userid " + userid)
            user_resp = self.NXC.nxc.get_user(userid)
            nxc_user_data = user_resp.data
            print ("got from NXC:",userid, user_resp.data["displayname"], user_resp.data['email'],user_resp.data['groups'])
            nxc_user = {}
            DisplayName = nxc_user_data["displayname"]
            # print (DisplayName)
            split = DisplayName.rfind(" ")
            if split > -1:
                Nachname = DisplayName[split+1:]
                Vorname = DisplayName[:split]
            else:
                Nachname = DisplayName
                Vorname = ""
            nxc_user["Vorname"] = Vorname.strip()
            nxc_user["Nachname"] = Nachname.strip()
            nxc_user["Email"] = nxc_user_data["email"].strip()
            nxc_user["Gruppen"] = nxc_user_data["groups"].strip()
            nxc_user["Userid"] = userid
            nxc_user["InitPwd"] = ""
            nxc_user["LastSync"] = self.time_now
            nxc_users[userid] = nxc_user
            if verbosity > 1:
                print("from NXC got detailed info for userid " + userid)
                print (json.dumps(nxc_users[userid], sort_keys=True,indent=2, separators=(',', ' : ')))
        print (nxc_users)
        return nxc_users      

    def generate_new_users_from_csv(self):
        """
        uses csv.DictReader with delimiter=';'
        item keys are given by 
        item values in csv file are stripped from leading or trailing blanks etc
        groups can be provided by a comma (",") separated list inside a semicolon separated field 
        currently the item keys are given in german:
        "Vorname;Nachname;Email;Gruppen;Userid;InitPwd"
        """
        validUsers = {}
        with open(USER_INPUT_CSV_FILE) as csv_file:
            reader = csv.DictReader(csv_file, delimiter=';')
            # TODO: generalize from the following very specific item keys
            for row in reader:
                newUser = {}
                for item in row:
                    if not item in ["Userid","InitPwd"]:
                        newUser[item] = row[item].strip()
                newUser["Userid"] = self.generate_username(row["Vorname"],row["Nachname"])
                if row["Userid"] != "":
                    print("Warning: new user " + row["Vorname"] + " " + row["Nachname"] + " has already a Userid: " + row["Userid"])
                elif self.NXC.check_new_user(newUser):
                    newUser["InitPwd"] = self.generate_pwd(PASSWORD_LG)
                    newUser["Gruppen"] = newUser["Gruppen"].replace(","," ").replace("  "," ").split(" ")
                    newUser["LastSync"] = self.time_now
                    validUsers[newUser["Userid"]] = newUser
        return validUsers
            
    def update_csv_file(self,new_rows):
        # old_rows = []
        # with open(USER_CSV_FILE) as csv_file:
        #     reader = csv.DictReader(csv_file, delimiter=';', quotechar='"')
        #     for row in reader:
        #         old_rows.append(row)
        fieldnames = ['Userid','Vorname','Nachname','Email','Gruppen','InitPwd','LastSync']
        os.rename(USER_CSV_FILE,USER_CSV_FILE + "-" + self.time_now)
        with open(USER_CSV_FILE, mode='w') as csv_file:
            writer = csv.writer(csv_file, delimiter=';', quotechar='"')
            writer = csv.DictWriter(csv_file, delimiter=';', fieldnames=fieldnames)
            writer.writeheader()
            for userdata in self.users:
                writer.writerow(self.users[userdata])
            for userdata in self.nxc_users:
                writer.writerow(self.nxc_users[userdata])
            for userdata in new_rows:
                writer.writerow(new_rows[userdata])        
        return

    def synchronize_csv_file(self,users):
        # old_rows = []
        # with open(USER_CSV_FILE) as csv_file:
        #     reader = csv.DictReader(csv_file, delimiter=';', quotechar='"')
        #     for row in reader:
        #         old_rows.append(row)
        fieldnames = ['Userid','Vorname','Nachname','Email','Gruppen','InitPwd','LastSync']
        os.rename(USER_CSV_FILE,USER_CSV_FILE + "-" + self.time_now)
        with open(USER_CSV_FILE, mode='w') as csv_file:
            writer = csv.writer(csv_file, delimiter=';', quotechar='"')
            writer = csv.DictWriter(csv_file, delimiter=';', fieldnames=fieldnames)
            writer.writeheader()
            for userdata in users:
                writer.writerow(users[userdata])        
        return

    def mark_deleted_user(self,userid):
        if userid != None:
            for userdata in self.users:
                if self.users[userdata] == userid:
                    self.users[userdata]["Userid"] = '<--' + userid + '!-->'
        return self.users

    def get_existing_rows_from_csv(self):
        old_rows = []
        with open(USER_CSV_FILE) as csv_file:
            reader = csv.DictReader(csv_file, delimiter=';')
            for row in reader:
                old_rows.append(row)
        return old_rows

    def generate_pwd(self,lg):
        letters = string.ascii_letters
        digits = string.digits
        special_chars = string.punctuation
        special_chars1 = '!#$%&\()*+,-./:;<=>?@[]^_{|}~'
        alphabet = letters + digits + digits + special_chars1
        pwd = ''
        for i in range(lg):
            pwd += ''.join(secrets.choice(alphabet))
        return pwd    
    
    def generate_username(self,name,surname):
        names = name.replace("-"," ").split(" ")
        surnames = surname.replace("-"," ").split(" ")
        username = names[0].capitalize()
        for item in names[1:]:
            username += item[0].upper()
        username += surname[0].upper()
        for item in surnames[1:]:
            username += item[0].upper()
        return username

    def get_timenow(self):
        format_time = "%Y%m%d-%H%M"
        dtn = datetime.datetime.now()
        format = "%Y%m%d-%H%M"
        dt_str = datetime.datetime.strftime(dtn,format)
        return dt_str


#########################        
class Nextcloud_Environment():

    def __init__(self):
        try:
            self.credfile = open(BEGOE_ADMIN_CRED,"r")
        except:
            print("Error: credential file not found! at " + BEGOE_ADMIN_CREDS)
            sys.exit(1)
        self.credstr = self.credfile.read()
        self.cred = json.loads(self.credstr)
        self.NEXTCLOUD_URL = self.cred['baseuri']
        self.NEXTCLOUD_USERNAME = self.cred['username']
        self.NEXTCLOUD_PASSWORD = self.cred['password']
        self.nxc = self.get_access()
        self.users_resp = self.nxc.get_users()
        self.groups_resp = self.nxc.get_groups()
        self.users_exist = self.users_resp.data["users"]
        self.groups_exist = self.groups_resp.data["groups"]
        self.user_content = {}
        self.email_for_users = []
        self.group_for_users = []
        self.Mail = Mailing(relay=False)
        # self.get_user_environment()
        
    def get_access(self):
        nxc = NextCloud(endpoint=self.NEXTCLOUD_URL, user=self.NEXTCLOUD_USERNAME, password=self.NEXTCLOUD_PASSWORD)
        return nxc

    def get_user_environment(self):
        print("getting existing users and groups ...")
        for userid in self.users_resp.data['users']:
            user_resp = self.nxc.get_user(userid)
            self.user_content[userid] = user_resp.data
            print (userid, user_resp.data["displayname"], user_resp.data['email'],user_resp.data['groups'])
            self.email_for_users.append(user_resp.data['email'])
            self.group_for_users.append(user_resp.data['groups'])
        print (json.dumps(self.user_content, sort_keys=True,indent=2, separators=(',', ' : ')))
        return self.user_content
    
    def add_users(self, new_users):
        failed_users = {} 
        added_users = {}
        for userid in new_users:
            user_content = new_users[userid]         
            user_resp = self.add_single_user(user_content)
            if user_resp != None and user_resp.status_code == 100:
                added_users[userid] = user_content
            else: 
                failed_users[userid] = user_content
        return added_users, failed_users

    def add_single_user(self, user_content):
        print (user_content["Userid"],user_content["InitPwd"],user_content["Email"],user_content["Gruppen"])
        print ("Do you want to add this user? [yes|No]")
        ans = sys.stdin.readline()
        if ans != "yes\n":
            return None
        user_resp = self.nxc.add_user(user_content["Userid"],user_content["InitPwd"])
        print ("add_user:      userid",user_resp.status_code, user_resp.data)
        user_resp = self.nxc.edit_user(user_content["Userid"],"displayname",user_content["Vorname"] + " " +  user_content["Nachname"])
        print ("edit_user: displayname",user_resp.status_code, user_resp.data)
        user_resp = self.nxc.edit_user(user_content["Userid"],"email",user_content["Email"])
        print ("edit_user:       email",user_resp.status_code, user_resp.data)
        # user_resp = self.nxc.edit_user(user_content["Userid"],"manager",self.nxc.user)
        # print (user_resp, user_resp.data)
        for group in user_content["Gruppen"]:
            user_resp = self.nxc.add_to_group(user_content["Userid"],group)
            print ("add_to_group " + group,user_resp.status_code, user_resp.data)
        # user_resp = self.nxc.resend_welcome_mail(user_content["Userid"])
        # print ("resend_welcome_mail",user_resp.status_code, user_resp.data)
        user_resp = self.nxc.get_user(user_content["Userid"])
        subject = "Zugang zur Team-Umgebung der Bürgerenergie Göttingen unter der Userid '" + user_content["Userid"]
        prefix = "Liebe(r) " + user_content["Vorname"] + " " + \
            user_content["Nachname"] + " " + ",\n\nmit der Userid: \n\n<b>" + \
            user_content["Userid"] + "</b> \n\n" # + \
            # "und dem initialen Passwort:\n\n<b>" + \
            # user_content["InitPwd"] + "</b>\n\n"
        if SEND_USER_MSG:
            self.Mail.mail_message(user_content["Userid"],user_content["Email"], subject, prefix, USER_WELCOME_FILE)
        return user_resp

    def check_new_user(self,newUser):
        user_OK = True
        new_userid = newUser['Userid']
        new_email = newUser['Email']
        if new_userid in self.users_exist:
            user_OK = False
            print ("Error: new user_id " + new_userid + " does already exist!")
            print("add new user with modified userid? [yes|No]")
            ans = sys.stdin.readline()
            if ans != "yes\n":
                user_OK = False
            else: # try to append digit 1..9 to userid
                user_OK = False
                for i in range(1,9):
                     if new_userid + str(i) not in self.users_exist:
                         print("modify userid to " + new_userid + str(i) + " ? [yes|No]")
                         ans = sys.stdin.readline()
                         if ans == "yes\n":
                             newUser['Userid'] += i
                             user_OK = True
                if not user_OK:
                    print ("Error: no possible digit extension found for userid " + new_userid)
        elif new_email in self.email_for_users: # works only if self.email_exist is filled
            old_user = self.users_exist[self.email_for_users.index(new_email)]
            print ("Warning: email " + new_email + " for new user_id " + new_userid + " does already exists for user: " + old_user)
            print("add new user anyway? [yes|No]")
            ans = sys.stdin.readline()
            if ans != "yes\n":
                user_OK = False
        return user_OK

    def user_info(self,userid,delete=None):
        try:
            user_resp = self.nxc.get_user(userid)
            if user_resp.status_code != 100:
                print ("user " + userid + " does not exist" )
                return None, None
            else:
                print (json.dumps(user_resp.data, sort_keys=True,indent=2, separators=(',', ' : ')))
        except:
            print ("user " + userid + " does not exist" )
        deleted_resp = None
        if delete:
            deleted_user = self.delete_user(userid,user_resp)
        return user_resp.data, deleted_user

    def get_user_attributes(self, userid):
        user_content = {}
        user_content["Vorname"] = self.ask_attr("Vorname")
        user_content["Nachname"] = self.ask_attr("Nachname")
        user_content["email"] = self.ask_attr("email")
        user_content["Userid"] = userid
        LocalUserDB = Local_User_DB(self)
        user_content["InitPwd"] = LocalUserDB.generate_pwd(PASSWORD_LG)
        print (user_content)

    def ask_attr(self, topic):
        print ("Input for '" + topic + "' : ")
        ans = sys.stdin.readline()[:-1]
        return ans
            
    def delete_user(self,userid,user_resp):
        user_email = user_resp.data["email"]
        user_name =  user_resp.data["displayname"]
        deleted_user = None
        # for user in user_rows:
        #     if user["Userid"] == userid:
        #         user_email = user["Email"]
        print ("Do you want to delete this user " + userid + " [yes|No]): ")
        ans = sys.stdin.readline()
        if ans == "yes\n":
            print ("Really???")
            ans = sys.stdin.readline()
            if ans == "yes\n":
                user_resp = self.nxc.delete_user(userid)
                if user_resp.status_code == 100:
                    print ("user",userid,"deleted")
                    subject = "Löschung der Userid '" + userid + "' von der Nextcloud der Bürgerenergie Göttingen"
                    prefix = "Liebe(r) " + user_name + ",\n\ndeine Userid: \n\n<b> " + userid + " </b> \n\n"
                    if SEND_USER_MSG:
                        self.Mail.mail_message(userid,user_email, subject, prefix, USER_FAREWELL_FILE)
                    deleted_user = userid
                else:
                    print ("user",userid,"deletion failed with rc:",user_resp.status_code)
            else:
                print("nothing done with user " + userid)
        else:
            print("nothing done with user " + userid)
        return deleted_user
    
#########################        

def info_or_delete(NXC,LocalUserDB,username):    
    print ("Infos for",username)
    old_rows = LocalUserDB.get_existing_rows_from_csv()
    user_data, deleted_data = NXC.user_info(username,old_rows)
    if deleted_data != None:
        LocalUserDB.mark_deleted_user(deleted_data)
        LocalUserDB.update_csv_file({})

def get_nextcloud_info(args):
    NXC = Nextcloud_Environment()
    # LocalUserDB = Local_User_DB(NXC)
    print("currently existing users in nextcloud:  " + str(NXC.users_exist))
    print("currently existing groups in nextcloud: " + str(NXC.groups_exist)) 
    userid = args.get_nextcloud_info
    if userid != "dummy":
        print ("attributes stored in nextcloud for user " + userid)
        user_content = NXC.user_info(userid)

def get_local_csv_info(args):
    NXC = Nextcloud_Environment()
    LocalUserDB = Local_User_DB(NXC)
    print("locally stored users:  " + str(LocalUserDB.users))
    userid = args.get_local_csv_info
    user_content = None
    if userid != "dummy":
        print ("attributes stored in nextcloud for user " + userid)
        user_content = NXC.user_info(userid)
    return user_content 

def add_user_from_csv_info(args):
    NXC = Nextcloud_Environment()
    LocalUserDB = Local_User_DB(NXC)
    dnow = LocalUserDB.get_timenow()
    # groups_exist, users_exist, email_exist, group_exist = get_existing_users(nxc)
    print("currently existing groups: " + str(NXC.groups_exist)) 
    print("currently existing users:  " + str(NXC.users_exist))
    print("existing email to users:   " + str(NXC.email_for_users))
    print("existing groups to users:  " + str(NXC.group_for_users))
    localUsers = LocalUserDB.users
    proposedUsers = LocalUserDB.generate_new_users_from_csv()
    userid = args.add_user_from_parameter
    if userid != "dummy" and userid in proposedUsers:
        proposedUsers_new = {}
        proposedUsers_new[userid] = proposedUsers[userid]
        proposedUsers = proposedUsers_new
    addedUsers, failedUsers = NXC.add_users(proposedUsers)
    print("Vorherige Nutzer:\n",localUsers)
    print("Neu eingetragene Nutzer:\n",addedUsers)
    print("Nicht eingetragene Nutzer:\n",failedUsers)
    LocalUserDB.update_csv_file(addedUsers)
  
    
def add_user_from_parameter(args):
    NXC = Nextcloud_Environment()
    NXC.get_user_attributes(args.add_user_from_parameter)
        
def delete_user_from_nextcloud(args):
    NXC = Nextcloud_Environment()
    LocalUserDB = Local_User_DB(NXC)
    userid = args.delete_user_from_nextcloud
    print ("Infos for",userid)
    old_rows = LocalUserDB.get_existing_rows_from_csv()
    user_data, deleted_data = NXC.user_info(userid,old_rows)
    if deleted_data != None:
        LocalUserDB.mark_deleted_user(deleted_data)
        LocalUserDB.update_csv_file({})

def synchronize_users_from_nextcloud(args):
    NXC = Nextcloud_Environment()
    LocalUserDB = Local_User_DB(NXC)
    userid = args.synchronize_users_from_nextcloud
    if  userid != "dummy":
        user_content = get_local_csv_info(args)        
    else:
        nxc_users = LocalUserDB.update_with_nextcloud_userids(None)
    LocalUserDB.synchronize_csv_file(nxc_users)
    
if __name__ == "__main__":
    defaultID = "dummy"
    defaultObject = {}
    verbosity = 1

    parser = argparse.ArgumentParser(description="nextcloud administration tool for BEGö team environment")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbose", action="store_true")
    group.add_argument("-q", "--quiet", action="store_true")
    # parser.add_argument("-T", "--Test", help="test struct",nargs='?', const="-1", action="store")
    parser.add_argument("-i", "--get_nextcloud_info", help="get user and group info from nextcloud", nargs='?', const=defaultID, action="store")
    parser.add_argument("-l", "--get_local_csv_info", help="get user and group info from local csv file",nargs='?', const=defaultID, action="store")
    parser.add_argument("-a", "--add_user_from_csv_info", help="add user from local csv file",nargs='?', const=defaultID, action="store")
    parser.add_argument("-A", "--add_user_from_parameter", help="add user from parameter object",nargs='?', const=defaultObject, action="store")
    parser.add_argument("-d", "--delete_user_from_nextcloud", help="delete user from nextcloud",nargs='?', const=defaultObject, action="store")
    parser.add_argument("-s", "--synchronize_users_from_nextcloud", help="synchronize users from nextcloud to local user csv", nargs='?', const=defaultID, action="store")
    # parser.add_argument("-o", "--get_list_of_others", help="gets a list of the dependent types of a type arg[0], that have another prefix than arg[1]",nargs='?', type=str, const=defaultID, action="store")
    # parser.add_argument("-u", "--url_of_type_registry", help="url of type registry (e.g. http://dtr-test.pidconsortium.net/)", action="store")
    # parser.add_argument("-C", "--credential_file", help="the full path to the credential file (default ./Credentials.txt)", type=str, action="store") 


    args = parser.parse_args()
    arg_found = False
    if args.quiet:
        arg_found = True
        verbosity = 0
    if args.verbose:
        arg_found = True
        verbosity = 2
    # if args.Test:
    #     Test(args)
    if args.get_nextcloud_info:
        arg_found = True
        get_nextcloud_info(args)
    if args.get_local_csv_info:
        arg_found = True
        get_local_csv_info(args)
    if args.add_user_from_csv_info:
        arg_found = True
        add_user_from_csv_info(args)
    if args.add_user_from_parameter:
        arg_found = True
        add_user_from_parameter(args)
    if args.delete_user_from_nextcloud:
        arg_found = True
        delete_user_from_nextcloud(args)
    if args.synchronize_users_from_nextcloud:
        arg_found = True
        synchronize_users_from_nextcloud(args)
    if not arg_found:
        print("Error: at least one argument is required: try -h")








# new_user_id = "new_user_username"
# add_user_res = nxc.add_user(new_user_id, "new_user_password321_123")
# group_name = "new_group_name"
# add_group_res = nxc.add_group(group_name)
# add_to_group_res = nxc.add_to_group(new_user_id, group_name)
# groups=nxc.get_groups()
# print(groups.data)
# groups=nxc.get_group('Projektentwicklung')
# print(group.data)
