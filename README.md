# Google Single Sign-On Demo

A Windows desktop demo for an Enterprise Application Integration course. Both applications use Google as their identity provider and run in separate Python processes. They use Python's standard library and Tkinter, with no packages to install.

| Application | Launch command | Credentials |
| --- | --- | --- |
| A — Employee HR Portal (window titled Enterprise Employee Portal) | `python main.py` | `credentials.json` |
| B — Inventory Management Portal | `python inventory_app.py` | `inventory_credentials.json` if present, otherwise `credentials.json` |

Keep both Python files in the same folder because the inventory app imports the HR portal's OAuth and sign-in code. The original HR application is backed up as `main.py.bak`.

If the HR portal already signs in successfully, skip to the optional second client below or go straight to the demo.

## 1. Create a Google Cloud project

1. Sign in to the [Google Cloud Console](https://console.cloud.google.com/).
2. Open the project selector at the top and choose **New Project**.
3. Name the project **Enterprise Employee Portal**, choose a location if prompted, and click **Create**.
4. Select your new project in the project selector before continuing.

## 2. Configure the OAuth consent screen

1. Open [Google Auth Platform → Branding](https://console.cloud.google.com/auth/branding) and click **Get started** if prompted.
2. Enter **Enterprise Employee Portal** as the app name and select a user support email.
3. Choose **External** to use a personal Google account. Choose **Internal** only if your project belongs to a Google Workspace organization and everyone signing in belongs to that organization.
4. Enter a developer contact email, accept the policy if prompted, and click **Create**.
5. In **Data Access**, the only scopes relevant to this demo are `openid`, `https://www.googleapis.com/auth/userinfo.email`, and `https://www.googleapis.com/auth/userinfo.profile`. The application requests their equivalents `openid email profile` at sign-in.
6. For an External demo, you can keep **Audience** in **Testing**. Google exempts these basic identity scopes from the test-user list requirement. [Google's audience settings](https://support.google.com/cloud/answer/15549945?hl=en)

## 3. Create and download desktop credentials

1. Open [Google Auth Platform → Clients](https://console.cloud.google.com/auth/clients).
2. Choose **Create client**, set **Application type** to **Desktop app**, enter a name such as **Employee Portal Desktop**, and click **Create**. The app uses a loopback address with a port picked at runtime, so there is no redirect URI to enter in the console. [Google's desktop OAuth guide](https://developers.google.com/identity/protocols/oauth2/native-app)
3. In the creation dialog, click **Download JSON** and save the file while the dialog is open. [Google's client management guide](https://support.google.com/cloud/answer/15549257?hl=en)
4. Rename the downloaded file to **credentials.json** and put it in the same folder as **main.py**. With file extensions visible in File Explorer, check that the name ends in a single `.json`. Keep that file out of shared submissions and version control. The project's Git ignore rules cover the renamed file and Google's usual download filename.

### Optional second OAuth client

You can demonstrate browser-session reuse immediately with the existing `credentials.json`. In that setup, Google sees both processes as the same OAuth client. For a clearer demonstration of two separately registered applications, create a second **Desktop app** client named **Inventory Portal Desktop** in the same Google Cloud project. Download its JSON and save it beside `inventory_app.py` as `inventory_credentials.json`. Restart the inventory app if it was already open. The HR app continues to use `credentials.json`. Keep both JSON files private. [Google's desktop OAuth guide](https://developers.google.com/identity/protocols/oauth2/native-app)

## 4. Run and demonstrate SSO

Use a Python 3 installation with Tkinter. To check Tkinter, run `python -m tkinter` in PowerShell and close the test window. Open two PowerShell windows in the project folder. In the first, launch the HR portal.

```powershell
python main.py
```

1. Click **Sign in with Google** in the HR portal and complete Google's prompts. Keep the HR portal open on its welcome dashboard.
2. In the second PowerShell window, run `python inventory_app.py`.
3. Click **Sign in with Google** in the inventory portal. Both apps open the system's default browser. Use the same browser profile and select the same Google account if the account chooser appears. With an active Google session, Google can let you continue without entering the password again. Google may still ask for consent or reauthentication. [Google's OpenID Connect reference](https://developers.google.com/identity/openid-connect/reference)
4. Compare the name and email on the two dashboards. The inventory portal also shows sample stock.
5. Click **Log out** in the inventory portal and show that the HR dashboard is still signed in. You can repeat the test in the opposite direction.

If your Windows installation uses the Python launcher, replace `python` with `py` in the commands.

Each application starts its own localhost callback, verifies its own random `state`, exchanges its one-time code with its own PKCE verifier, and requests its profile from Google UserInfo over HTTPS. Each portal clears its own in-memory profile on logout. The browser's Google session can persist across both local logouts. [Google's published OpenID Connect endpoints](https://accounts.google.com/.well-known/openid-configuration)

## Troubleshooting

- **Missing or invalid credentials**. Confirm the exact filename and check that you downloaded a **Desktop app** client. The JSON should have an `installed` section.
- **Google rejects the request**. Check the client type and the Google error shown in the browser. If a university-managed account is blocked by organization policy, try a personal Google account with an External project.
- **Closed the browser or changed your mind**. Click **Cancel** in the portal to stop waiting. The callback also times out after three minutes.

To verify live SSO, complete the demo above with your Google account and confirm that both apps show your identity and that logging out in one leaves the other signed in.
