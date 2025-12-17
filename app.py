import viktor as vkt
import requests


# Base URLs for Trimble Connect API (US region)
BASE_URL = "https://app.connect.trimble.com"
API_BASE = f"{BASE_URL}/tc/api/2.0"


# HTML template for Trimble Connect Viewer
VIEWER_HTML_TEMPLATE = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Trimble Connect Viewer</title>
    <style>
      html, body {
        margin: 0;
        padding: 0;
        height: 100%;
        width: 100%;
        overflow: hidden;
      }
      #tc-viewer {
        border: 0;
        width: 100%;
        height: 100%;
      }
    </style>
    <script src="https://components.connect.trimble.com/trimble-connect-workspace-api/index.js"></script>
  </head>
  <body>
    <iframe
      id="tc-viewer"
      src="about:blank"
      allowfullscreen
    ></iframe>

    <script>
      const ACCESS_TOKEN = "__ACCESS_TOKEN__";
      const PROJECT_ID   = "__PROJECT_ID__";
      const MODEL_ID     = "__MODEL_ID__";
      const VERSION_ID   = "__VERSION_ID__";

      (async function () {
        try {
          const iframe = document.getElementById("tc-viewer");

          // Get Trimble's embedded app URL
          iframe.src = TrimbleConnectWorkspace.getConnectEmbedUrl();

          // Connect Workspace API to the iframe
          const api = await TrimbleConnectWorkspace.connect(
            iframe,
            function (event, data) {
              console.log("TC event:", event, data);
            },
            30000
          );

          // Pass the OAuth access token
          await api.embed.setTokens({
            accessToken: ACCESS_TOKEN
          });

          // Configure which project/model to open
          const config = {
            projectId: PROJECT_ID,
            modelId: MODEL_ID
          };

          if (VERSION_ID) {
            config.versionId = VERSION_ID;
          }

          // Start 3D viewer
          await api.embed.init3DViewer(config);
        } catch (e) {
          console.error("Error initializing Trimble viewer:", e);
          alert("Failed to initialize Trimble Connect viewer. Check console.");
        }
      })();
    </script>
  </body>
</html>
"""


def build_trimble_viewer_html(access_token: str,
                              project_id: str,
                              model_id: str,
                              version_id: str | None = None) -> str:
    """
    Return a complete HTML document that shows a Trimble Connect model.

    access_token: OAuth2 access token for the Trimble user
    project_id:   Trimble Connect project id (e.g. 'GUiM8Tk3nTo')
    model_id:     File / model id (e.g. 'ETNppTylU6c')
    version_id:   Optional model version id
    """
    html = VIEWER_HTML_TEMPLATE
    html = html.replace("__ACCESS_TOKEN__", access_token)
    html = html.replace("__PROJECT_ID__", project_id)
    html = html.replace("__MODEL_ID__", model_id)
    html = html.replace("__VERSION_ID__", version_id or "")

    return html


def get_trimble_projects(**kwargs):
    """Fetch all projects from Trimble Connect"""
    try:
        # Get the OAuth2 token
        integration = vkt.external.OAuth2Integration("trimble-connect")
        token = integration.get_access_token()
        
        # Set up headers with the access token
        headers = {"Authorization": f"Bearer {token}"}
        
        # Fetch projects from Trimble Connect API
        url = f"{API_BASE}/projects"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        projects = response.json()
        
        # Create option list with project names and IDs
        options = [vkt.OptionListElement(value=project["id"], label=project["name"]) 
                   for project in projects]
        
        return options if options else [vkt.OptionListElement(value="", label="No projects found")]
    
    except Exception as e:
        return [vkt.OptionListElement(value="error", label=f"Error loading projects: {str(e)}")]


def get_project_files(params, **kwargs):
    """Fetch all files from the selected Trimble Connect project"""
    # Only fetch files if a project is selected
    if not params.project:
        return [vkt.OptionListElement(value="Select a Project First", label="Select a Project First")]
    
    try:
        # Get the OAuth2 token
        integration = vkt.external.OAuth2Integration("trimble-connect")
        token = integration.get_access_token()
        
        # Fetch project details to get root folder ID
        project_url = f"{API_BASE}/projects/{params.project}"
        headers = {"Authorization": f"Bearer {token}"}
        
        proj_resp = requests.get(project_url, headers=headers)
        proj_resp.raise_for_status()
        
        root_id = proj_resp.json().get("rootId")
        
        if not root_id:
            return [vkt.OptionListElement(value="", label="Could not find root folder")]
        
        # Recursively list all files
        def list_folder(folder_id, current_path=""):
            """Recursively walk through folders and collect files"""
            url = f"{API_BASE}/folders/{folder_id}/items"
            
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            items = resp.json()

            files = []

            for item in items:
                name = item.get("name", "")
                item_id = item.get("id")
                item_type = (item.get("type") or item.get("entityType") or "").upper()
                item_path = f"{current_path}/{name}".lstrip("/")

                if item_type == "FOLDER":
                    files.extend(list_folder(item_id, item_path))
                else:
                    files.append({
                        "id": item_id,
                        "name": name,
                        "path": item_path,
                    })

            return files
        
        files = list_folder(root_id, "")
        
        # Create option list with file paths and IDs
        options = [vkt.OptionListElement(value=file["id"], label=file["path"]) 
                   for file in files]
        
        return options if options else [vkt.OptionListElement(value="", label="No files found in project")]
    
    except Exception as e:
        return [vkt.OptionListElement(value="error", label=f"Error loading files: {str(e)}")]


class Parametrization(vkt.Parametrization):
    """Parametrization for Trimble Connect OAuth2 test"""
    # Header and description
    text_header = vkt.Text("# Trimble Connect - Viktor Integration")
    text_description = vkt.Text(
        "This app integrates with Trimble Connect to browse projects and visualize 3D models. "
        "Select a project and file below, then download the viewer HTML to open it in your browser."
    )
    
    lb_1 = vkt.LineBreak()
    
    # Project and file selection
    project = vkt.OptionField("Select Project", options=get_trimble_projects)
    file = vkt.OptionField("Select File/Model", options=get_project_files, default="")
    
    lb_2 = vkt.LineBreak()
    
    # Download section
    text_download_description = vkt.Text("""## Download Viewer
Download a standalone HTML file that you can open in your browser to view the 3D model.
The file includes embedded credentials and will work without any additional setup.
"""
    )
    download_viewer_btn = vkt.DownloadButton("Download Viewer HTML", method="download_viewer_html")


class Controller(vkt.Controller):
    """Controller to test Trimble Connect OAuth2 integration"""
    parametrization = Parametrization

    def list_project_files(self, project_id, token):
        """
        Recursively list all files in a Trimble Connect project.

        Returns a list of dicts:
        [
          {
            "id": "<fileId>",
            "name": "SampleBuilding.ifc",
            "path": "Models/SampleBuilding.ifc",
            "size": 123456,
            "modifiedAt": "2025-12-16T12:34:56Z",
            "raw": {...original item JSON...}
          },
          ...
        ]
        """
        
        # 1. Fetch Project Details to get the Root Folder ID
        project_url = f"{API_BASE}/projects/{project_id}"
        headers = {"Authorization": f"Bearer {token}"}
        
        proj_resp = requests.get(project_url, headers=headers)
        proj_resp.raise_for_status()
        
        # Extract the rootId from the project response
        root_id = proj_resp.json().get("rootId")
        
        if not root_id:
            raise Exception("Could not find root folder ID for this project.")
        
        def list_folder(folder_id, current_path=""):
            """Recursively walk through folders and collect files"""
            # 2. Use the folder_id (starting with root_id) to list items
            url = f"{API_BASE}/folders/{folder_id}/items"
            
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            items = resp.json()

            files = []

            for item in items:
                name = item.get("name", "")
                item_id = item.get("id")
                # Handle type variations (API sometimes returns 'FOLDER' or 'FILE')
                item_type = (item.get("type") or item.get("entityType") or "").upper()

                # Build a pretty path
                item_path = f"{current_path}/{name}".lstrip("/")

                # Heuristic: treat explicit FOLDERs as folders, everything else as file-ish
                if item_type == "FOLDER":
                    files.extend(list_folder(item_id, item_path))
                else:
                    files.append(
                        {
                            "id": item_id,
                            "name": name,
                            "path": item_path,
                            "size": item.get("size"),
                            "modifiedAt": item.get("modifiedAt") or item.get("modifiedOn"),
                            "raw": item,
                        }
                    )

            return files

        # 3. Start recursion with the Root Folder ID, not the Project ID
        return list_folder(root_id, "")

    @vkt.DataView("Token Info", duration_guess=40)
    def test_oauth2_token(self, params, **kwargs):
        """Test the OAuth2 integration and display token information"""
        # Initialize the OAuth2 integration with the configured name
        integration = vkt.external.OAuth2Integration("trimble-connect")
        
        # Retrieve the access token
        access_token = integration.get_access_token()
        
        # Create a data group to display token information
        data_group = vkt.DataGroup()
        
        # Display token details for verification
        data_group.add(
            vkt.DataItem("Integration Name", "trimble-connect", status=vkt.DataStatus.INFO),
            vkt.DataItem("Token Retrieved", "Success", status=vkt.DataStatus.SUCCESS),
            vkt.DataItem("Access Token (first 20 chars)", access_token[:20] + "...", status=vkt.DataStatus.INFO),
            vkt.DataItem("Token Length", len(access_token), suffix="characters", status=vkt.DataStatus.INFO),
        )
        
        # If a project is selected, show project info and list files
        if params.project and params.project != "error":
            data_group.add(
                vkt.DataItem("Selected Project ID", params.project, status=vkt.DataStatus.INFO)
            )
            
            try:
                # List all files in the selected project
                files = self.list_project_files(params.project, access_token)
                data_group.add(
                    vkt.DataItem("Total Files Found", len(files), status=vkt.DataStatus.SUCCESS)
                )
                
                # Show first few files as examples
                if files:
                    file_subgroup = vkt.DataGroup()
                    for i, file in enumerate(files[:5]):  # Show first 5 files
                        file_subgroup.add(
                            vkt.DataItem(f"File {i+1}", file["path"], status=vkt.DataStatus.INFO)
                        )
                    if len(files) > 5:
                        file_subgroup.add(
                            vkt.DataItem("...", f"and {len(files) - 5} more files", status=vkt.DataStatus.INFO)
                        )
                    data_group.add(
                        vkt.DataItem("Sample Files", subgroup=file_subgroup)
                    )
            except Exception as e:
                data_group.add(
                    vkt.DataItem("File Listing Error", str(e), status=vkt.DataStatus.ERROR)
                )
        
        return vkt.DataResult(data_group)

    def download_viewer_html(self, params, **kwargs):
        """Download the Trimble Connect viewer as a standalone HTML file"""
        # Check if both project and file are selected
        if not params.project or params.project == "error":
            raise vkt.UserError("Please select a project first")
        
        if not params.file or params.file == "error" or params.file == "":
            raise vkt.UserError("Please select a file/model to download the viewer for")
        
        # Get the OAuth2 access token
        integration = vkt.external.OAuth2Integration("trimble-connect")
        access_token = integration.get_access_token()
        
        # Build the HTML viewer with the selected project and file
        html = build_trimble_viewer_html(
            access_token=access_token,
            project_id=params.project,
            model_id=params.file,
            version_id=None  # Optional: can be extended to support version selection
        )
        
        # Create a file from the HTML string
        html_file = vkt.File.from_data(html)
        
        # Return as downloadable file
        return vkt.DownloadResult(html_file, "trimble_connect_viewer.html")

    @vkt.WebView("3D Viewer", duration_guess=1)
    def show_trimble_viewer(self, params, **kwargs):
        """Display the selected file in the Trimble Connect 3D viewer"""
        # Check if both project and file are selected
        if not params.project or params.project == "error":
            return vkt.WebResult(html="<h2>Please select a project first</h2>")
        
        if not params.file or params.file == "error" or params.file == "":
            return vkt.WebResult(html="<h2>Please select a file/model to visualize</h2>")
        
        # Get the OAuth2 access token
        integration = vkt.external.OAuth2Integration("trimble-connect")
        access_token = integration.get_access_token()
        
        # Build the HTML viewer with the selected project and file
        html = build_trimble_viewer_html(
            access_token=access_token,
            project_id=params.project,
            model_id=params.file,
            version_id=None  # Optional: can be extended to support version selection
        )
        
        return vkt.WebResult(html=html)