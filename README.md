## Prerequisites 
To create an integration using Trimble Connect, the administrator's email must be an organizational email. Personal subscriber and personal emails (e.g., @gmail, outlook, yahoo) are not eligible for API access.

Your organization should have a subscription plan. Go to the [Trimble Connect webpage](https://www.trimble.com/en/products/trimble-connect) and make sure you have either a "Pro" or "Innovative" plan.

# Creating a Project in Trimble Connect
In your Trimble Connect dashboard, you can manage or create a new project. This project will be connected to the VIKTOR application. If there is no project yet, you can click on "New" and fill in the form to create one.

assets\create_app.png

:::note
It is important to note the region where the application is hosted because the APIs to use depend on the region, as we will see later.
:::

## Request API Credentials 
The administrator should go to the Trimble [developer page](https://developer.tekla.com/documentation/integrating-trimble-connect) and request API credentials. The form should be filled with your account information, the **Application Name**, and the **Sign-In Redirect URL (OAuth 2.0)**.

The application name is important because it will be used to request an authorization token. Make sure to use a unique name. For demonstration purposes, the image below uses `my-viktor-integration`, but make sure to use something unique and specific for your case.

For the Sign-In Redirect URL (OAuth 2.0), you will provide a URL based on your VIKTOR environment.

```plaintext
<your-viktor-environment-url>/api/integrations/oauth2/callback/
```

Your environment URL should be `https://cloud.viktor.ai/` or similar, depending on your organization. As an example, we will use `https://cloud.viktor.ai/api/integrations/oauth2/callback/`, but make sure to use the proper environment URL.

assets\cross_error.png

After filling in the form, you will receive an email from the Trimble support team within the next 72 hours:

```plaintext
Application Name: my-viktor-integration 

Client ID: a1d022e6-....

Client Secret: ese18630...

Callback URLs: 
https://cloud.viktor.ai/api/integrations/oauth2/callback/
```

:::note
Make sure to confirm the callback URL matches your environment, otherwise the integration will fail.
:::

## Creating an OAuth 2.0 Integration (Admin)
First, an OAuth 2.0 generic integration must be set up by a VIKTOR admin.

1. Navigate to the Integrations tab in the Administrator panel.

2. Select the OAuth 2.0 tab.

3. Follow the steps in the modal:
   - Select **Generic**.
   - Go to the **"Basic Information"** tab and fill in the required fields, including the integration name, and select the applications that will use the integration. You can choose to limit the integration to specific apps or allow all apps in the environment to use it.
   - Then, in the "Configuration" tab, add the Authentication URL and Token URL as follows:
     - Authentication URL: https://id.trimble.com/oauth/authorize
     - Token URL: https://id.trimble.com/oauth/token

4. Fill in the **Client ID** and **Client Secret** from the email you received from Trimble support.

5. For the scope section, you will fill in: 

```plaintext
openid <ApplicationName>
```

As defined in the previous step, for the "my-viktor-integration" application name, the scope will be `openid my-viktor-integration`.

assets\viktor-integration-2.png


## Implementing the Integration in an App (Developer)

Once an administrator sets up and assigns the OAuth 2.0 integration to the app, the developer can start the implementation.

assets\final_integration.png

In your `viktor.config.toml`, add the integration:
```plaintext
app_type = "editor"
python_version = "3.13"
registered_name = "your-app-name"
oauth2_integrations = [
    "my-viktor-integration"
]
```

Then implement the logic that uses the integration in the code. You can use raw REST requests or a Python SDK, as long as it is compatible with the VIKTOR OAuth flow. A popular library is `requests`. You can add it in your `requirements.txt` to use it in the application.

```plaintext
viktor==14.26.0
requests
```

To obtain an access token, instantiate `OAuth2Integration` with the integration name and call `get_access_token`. Below is a short example showing how to retrieve the user's available projects and display them in a TableView. This works when the OAuth2 integration is assigned to your app and the user has granted access:

```python
import viktor as vkt
import requests

class Parametrization(vkt.Parametrization):
    text = vkt.Text("# Trimble Connect OAuth2 Integration")

class Controller(vkt.Controller):
    parametrization = Parametrization

    @vkt.TableView("Get Trimble Connect Projects")
    def get_projects(self, params, **kwargs):
        integration = vkt.external.OAuth2Integration("trimble-connect")
        token = integration.get_access_token()

        headers = {"Authorization": f"Bearer {token}"}
        endpoint = "https://app.connect.trimble.com/tc/api/2.0/projects"
        response = requests.get(endpoint, headers=headers, timeout=15)
        response.raise_for_status()

        projects = response.json()

        data = []
        for project in projects:
            project_name = project.get("name", "")
            project_id = project.get("id", "")
            data.append([project_name, project_id])

        return vkt.TableResult(data, column_headers=["Project Name", "ID"])
```