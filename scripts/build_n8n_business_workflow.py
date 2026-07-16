from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / "n8n" / "workflows"
OUTPUT = WORKFLOW_DIR / "mission-control-business-automation.json"
DRIVE_CREDENTIAL = {
    "googleDriveOAuth2Api": {
        "id": "__GOOGLE_DRIVE_CREDENTIAL_ID__",
        "name": "Google Drive account",
    }
}


def _load(name: str) -> dict[str, Any]:
    return json.loads((WORKFLOW_DIR / name).read_text(encoding="utf-8"))


def _folder_nodes(
    *, key: str, label: str, source: str, parent_expression: str, x: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    title = "Project" if key == "project" else label
    search = f"Search {title} Folder"
    select = f"Select {title} Folder"
    exists = f"{title} Folder Exists?"
    create = f"Create {title} Folder"
    finalize = f"Finalize {title} Folder"
    webhook = "$('Project Delivery Webhook').first().json.body"
    if key == "project":
        context = webhook
        folder_name = f"{webhook}.project.name"
        search_name = "={{ $('Project Delivery Webhook').first().json.body.project.name }}"
    else:
        context = f"$('Finalize {source} Folder').first().json"
        folder_name = json.dumps(label)
        search_name = label
    select_code = (
        f"const context = {context};\n"
        "const matches = $input.all().filter(item => item.json?.id);\n"
        f"const name = {folder_name};\n"
        "const exact = matches.find(item => item.json.name === name);\n"
        f"const configured = context.folders?.{key} || '';\n"
        "return [{ json: { ...context, folder_id: configured || exact?.json.id || '', folder_name: name } }];"
    )
    finalize_code = (
        f"const context = $('{select}').first().json;\n"
        "const folderId = $json.id || context.folder_id;\n"
        f"return [{{ json: {{ ...context, folders: {{ ...(context.folders || {{}}), {key}: folderId }} }} }}];"
    )
    nodes = [
        {
            "parameters": {
                "resource": "fileFolder",
                "operation": "search",
                "searchMethod": "name",
                "queryString": search_name,
                "returnAll": False,
                "limit": 20,
                "filter": {
                    "driveId": {"__rl": True, "mode": "list", "value": "My Drive"},
                    "folderId": {"__rl": True, "mode": "id", "value": parent_expression},
                    "whatToSearch": "folders",
                },
                "options": {},
            },
            "id": f"delivery-search-{key}",
            "name": search,
            "type": "n8n-nodes-base.googleDrive",
            "typeVersion": 3,
            "position": [x, 420],
            "alwaysOutputData": True,
            "credentials": DRIVE_CREDENTIAL,
        },
        {
            "parameters": {"jsCode": select_code},
            "id": f"delivery-select-{key}",
            "name": select,
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [x + 220, 420],
        },
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "typeValidation": "strict", "version": 2},
                    "conditions": [
                        {
                            "id": f"delivery-{key}-exists",
                            "leftValue": "={{ Boolean($json.folder_id) }}",
                            "rightValue": True,
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "id": f"delivery-if-{key}",
            "name": exists,
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [x + 440, 420],
        },
        {
            "parameters": {
                "resource": "folder",
                "name": "={{ $json.folder_name }}",
                "driveId": {"__rl": True, "mode": "list", "value": "My Drive"},
                "folderId": {"__rl": True, "mode": "id", "value": parent_expression},
                "options": {},
            },
            "id": f"delivery-create-{key}",
            "name": create,
            "type": "n8n-nodes-base.googleDrive",
            "typeVersion": 3,
            "position": [x + 660, 520],
            "credentials": DRIVE_CREDENTIAL,
        },
        {
            "parameters": {"jsCode": finalize_code},
            "id": f"delivery-finalize-{key}",
            "name": finalize,
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [x + 880, 420],
        },
    ]
    connections = {
        search: {"main": [[{"node": select, "type": "main", "index": 0}]]},
        select: {"main": [[{"node": exists, "type": "main", "index": 0}]]},
        exists: {
            "main": [
                [{"node": finalize, "type": "main", "index": 0}],
                [{"node": create, "type": "main", "index": 0}],
            ]
        },
        create: {"main": [[{"node": finalize, "type": "main", "index": 0}]]},
    }
    return nodes, connections


def build() -> dict[str, Any]:
    intake = _load("website-sales-heidelberg.json")
    lead = _load("website-sales-lead-processing.json")
    delivery = _load("project-delivery-sync.json")

    remove_intake = {
        "Create Mission Control Project",
        "BOSS Creates Mission Plan",
        "Approve & Materialize Tasks",
    }
    intake_nodes = [node for node in intake["nodes"] if node["name"] not in remove_intake]
    intake_connections = {
        key: value for key, value in intake["connections"].items() if key not in remove_intake
    }
    intake_connections["Requirements Complete?"]["main"][0] = [
        {"node": "Log Mission in Google Sheets CRM", "type": "main", "index": 0}
    ]
    log_node = next(node for node in intake_nodes if node["name"] == "Log Mission in Google Sheets CRM")
    values = log_node["parameters"]["columns"]["value"]
    values["Aktivitäts-ID"] = "={{ 'MISSION-' + $('Normalize Mission & Build Questions').first().json.data.project_id }}"
    values["Ergebnis"] = "Projekt angenommen und Aufgaben durch BOSS delegiert"
    values["Nächste Aktion"] = "Agenten arbeiten; Ergebnisse werden automatisch synchronisiert"
    response_node = next(node for node in intake_nodes if node["name"] == "Return Mission Started")
    response_node["parameters"]["responseBody"] = (
        "={{ JSON.stringify({ status: 'project_created', message: 'Mission läuft bereits in Mission Control.', "
        "project_id: $('Normalize Mission & Build Questions').first().json.data.project_id, "
        "mission_plan_id: $('Normalize Mission & Build Questions').first().json.data.mission_plan_id, "
        "task_count: $('Normalize Mission & Build Questions').first().json.data.task_count, research_status: 'queued' }) }}"
    )
    normalize = next(node for node in intake_nodes if node["name"] == "Normalize Mission & Build Questions")
    normalize["parameters"]["jsCode"] = normalize["parameters"]["jsCode"].replace(
        "const data = {", "const data = {\n  project_id: input.project_id,\n  mission_plan_id: input.mission_plan_id,\n  task_count: Number(input.task_count || 0),"
    )

    # Credentials are deployment-specific. Keep the generated workflow portable
    # and let sync_n8n_workflows.py inject the configured local credential IDs.
    for node in intake_nodes + lead["nodes"]:
        credentials = node.get("credentials", {})
        if "googleSheetsOAuth2Api" in credentials:
            credentials["googleSheetsOAuth2Api"]["id"] = "__GOOGLE_SHEETS_CREDENTIAL_ID__"
        if "gmailOAuth2" in credentials:
            credentials["gmailOAuth2"]["id"] = "__GMAIL_CREDENTIAL_ID__"

    remove_delivery = {
        "Create Project Delivery Folder",
        "Prepare Delivery Files",
        "Upload Artifacts to Google Drive",
        "Build Delivery Result",
        "Log Delivery in Google Sheets",
        "Return Delivery Result",
    }
    delivery_nodes = [node for node in delivery["nodes"] if node["name"] not in remove_delivery]
    delivery_connections: dict[str, Any] = {}
    hierarchy_nodes: list[dict[str, Any]] = []
    hierarchy_connections: dict[str, Any] = {}
    specs = [
        ("project", "Project", "Project", "={{ $('Project Delivery Webhook').first().json.body.root_folder_id }}"),
        ("crm", "CRM & Leads", "Project", "={{ $('Finalize Project Folder').first().json.folders.project }}"),
        ("websites", "Websites & Angebote", "CRM & Leads", "={{ $('Finalize Project Folder').first().json.folders.project }}"),
        ("results", "Berichte & Ergebnisse", "Websites & Angebote", "={{ $('Finalize Project Folder').first().json.folders.project }}"),
    ]
    prior = "Project Delivery Webhook"
    for index, (key, label, source, parent) in enumerate(specs):
        nodes, connections = _folder_nodes(
            key=key, label=label, source=source, parent_expression=parent, x=-420 + index * 1_160
        )
        hierarchy_nodes.extend(nodes)
        hierarchy_connections.update(connections)
        hierarchy_connections[prior] = {
            "main": [[{"node": f"Search {'Project' if key == 'project' else label} Folder", "type": "main", "index": 0}]]
        }
        prior = f"Finalize {'Project' if key == 'project' else label} Folder"

    crm_sheet_nodes = [
        {
            "parameters": {
                "resource": "fileFolder",
                "operation": "search",
                "searchMethod": "name",
                "queryString": "={{ 'Leads – ' + $('Project Delivery Webhook').first().json.body.project.name }}",
                "returnAll": False,
                "limit": 20,
                "filter": {
                    "driveId": {"__rl": True, "mode": "list", "value": "My Drive"},
                    "folderId": {"__rl": True, "mode": "id", "value": "={{ $('Finalize Berichte & Ergebnisse Folder').first().json.folders.crm }}"},
                    "whatToSearch": "files",
                },
                "options": {},
            },
            "id": "delivery-search-crm-sheet",
            "name": "Search Project CRM Sheet",
            "type": "n8n-nodes-base.googleDrive",
            "typeVersion": 3,
            "position": [4_220, 420],
            "alwaysOutputData": True,
            "credentials": DRIVE_CREDENTIAL,
        },
        {
            "parameters": {
                "jsCode": "const context = $('Finalize Berichte & Ergebnisse Folder').first().json;\nconst name = `Leads – ${context.project.name}`;\nconst exact = $input.all().find(item => item.json?.id && item.json.name === name);\nreturn [{ json: { ...context, crm_sheet_id: exact?.json.id || '', crm_sheet_name: name } }];"
            },
            "id": "delivery-select-crm-sheet",
            "name": "Select Project CRM Sheet",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [4_440, 420],
        },
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "typeValidation": "strict", "version": 2},
                    "conditions": [{"id": "delivery-crm-sheet-exists", "leftValue": "={{ Boolean($json.crm_sheet_id) }}", "rightValue": True, "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
                    "combinator": "and",
                },
                "options": {},
            },
            "id": "delivery-if-crm-sheet",
            "name": "Project CRM Sheet Exists?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [4_660, 420],
        },
        {
            "parameters": {
                "resource": "file",
                "operation": "copy",
                "fileId": {"__rl": True, "mode": "id", "value": "={{ $json.spreadsheet_id }}"},
                "name": "={{ $json.crm_sheet_name }}",
                "sameFolder": False,
                "driveId": {"__rl": True, "mode": "list", "value": "My Drive"},
                "folderId": {"__rl": True, "mode": "id", "value": "={{ $json.folders.crm }}"},
                "options": {"description": "Automatisch erzeugter CRM-Stand für dieses Mission-Control-Projekt."},
            },
            "id": "delivery-copy-crm-sheet",
            "name": "Copy CRM Sheet to Project",
            "type": "n8n-nodes-base.googleDrive",
            "typeVersion": 3,
            "position": [4_880, 520],
            "credentials": DRIVE_CREDENTIAL,
        },
        {
            "parameters": {
                "jsCode": "const context = $('Select Project CRM Sheet').first().json;\nconst id = $json.id || context.crm_sheet_id;\nreturn [{ json: { ...context, crm_sheet_id: id, crm_sheet_url: id ? `https://docs.google.com/spreadsheets/d/${id}` : '' } }];"
            },
            "id": "delivery-finalize-crm-sheet",
            "name": "Finalize Project CRM Sheet",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [5_100, 420],
        },
    ]
    hierarchy_nodes.extend(crm_sheet_nodes)
    hierarchy_connections[prior] = {"main": [[{"node": "Search Project CRM Sheet", "type": "main", "index": 0}]]}
    hierarchy_connections.update(
        {
            "Search Project CRM Sheet": {"main": [[{"node": "Select Project CRM Sheet", "type": "main", "index": 0}]]},
            "Select Project CRM Sheet": {"main": [[{"node": "Project CRM Sheet Exists?", "type": "main", "index": 0}]]},
            "Project CRM Sheet Exists?": {"main": [[{"node": "Finalize Project CRM Sheet", "type": "main", "index": 0}], [{"node": "Copy CRM Sheet to Project", "type": "main", "index": 0}]]},
            "Copy CRM Sheet to Project": {"main": [[{"node": "Finalize Project CRM Sheet", "type": "main", "index": 0}]]},
        }
    )

    prepare_code = """const input = $('Finalize Project CRM Sheet').first().json;
const artifacts = Array.isArray(input.artifacts) ? input.artifacts : [];
return artifacts.map((artifact) => {
  const text = `${artifact.name} ${artifact.artifact_type} ${artifact.media_type}`.toLowerCase();
  let bucket = 'results';
  if (/lead|crm|kontakt|e-mail|email/.test(text)) bucket = 'crm';
  else if (/website|angebot|html|css|javascript|typescript/.test(text)) bucket = 'websites';
  return {
    json: { artifact_key: artifact.key, artifact_name: artifact.name, project: input.project, spreadsheet_id: input.spreadsheet_id, folders: input.folders, target_folder_id: input.folders[bucket] },
    binary: { data: { data: artifact.content_base64, mimeType: artifact.media_type || 'application/octet-stream', fileName: artifact.name } },
    pairedItem: { item: 0 }
  };
});"""
    delivery_tail = [
        {
            "parameters": {"jsCode": prepare_code},
            "id": "delivery-prepare-files",
            "name": "Prepare Routed Delivery Files",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [5_340, 420],
        },
        {
            "parameters": {
                "operation": "upload",
                "inputDataFieldName": "data",
                "name": "={{ $binary.data.fileName }}",
                "driveId": {"__rl": True, "mode": "list", "value": "My Drive"},
                "folderId": {"__rl": True, "mode": "id", "value": "={{ $json.target_folder_id }}"},
                "options": {},
            },
            "id": "delivery-upload-routed",
            "name": "Upload Routed Artifacts",
            "type": "n8n-nodes-base.googleDrive",
            "typeVersion": 3,
            "position": [5_580, 420],
            "credentials": DRIVE_CREDENTIAL,
        },
        {
            "parameters": {
                "jsCode": "const uploaded = $input.all();\nconst source = $('Prepare Routed Delivery Files').all();\nconst context = $('Finalize Project CRM Sheet').first().json;\nconst artifactUrls = {};\nfor (let i = 0; i < uploaded.length; i++) { const key = source[i]?.json.artifact_key; const id = uploaded[i]?.json.id; if (key && id) artifactUrls[key] = `https://drive.google.com/open?id=${id}`; }\nreturn [{ json: { status: 'synced', project: context.project, spreadsheet_id: context.spreadsheet_id, crm_sheet_url: context.crm_sheet_url, artifact_count: uploaded.length, artifact_urls: artifactUrls, folders: context.folders, project_url: `https://drive.google.com/drive/folders/${context.folders.project}`, websites_url: `https://drive.google.com/drive/folders/${context.folders.websites}` } }];"
            },
            "id": "delivery-build-result",
            "name": "Build Routed Delivery Result",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [5_820, 420],
        },
    ]
    log_delivery = next(node for node in delivery["nodes"] if node["name"] == "Log Delivery in Google Sheets")
    log_delivery["position"] = [6_060, 420]
    return_delivery = next(node for node in delivery["nodes"] if node["name"] == "Return Delivery Result")
    return_delivery["parameters"]["responseBody"] = "={{ JSON.stringify($('Build Routed Delivery Result').first().json) }}"
    return_delivery["position"] = [6_300, 420]
    delivery_tail.extend([log_delivery, return_delivery])
    hierarchy_connections["Finalize Project CRM Sheet"] = {
        "main": [[{"node": "Prepare Routed Delivery Files", "type": "main", "index": 0}]]
    }
    hierarchy_connections.update(
        {
            "Prepare Routed Delivery Files": {"main": [[{"node": "Upload Routed Artifacts", "type": "main", "index": 0}]]},
            "Upload Routed Artifacts": {"main": [[{"node": "Build Routed Delivery Result", "type": "main", "index": 0}]]},
            "Build Routed Delivery Result": {"main": [[{"node": "Log Delivery in Google Sheets", "type": "main", "index": 0}]]},
            "Log Delivery in Google Sheets": {"main": [[{"node": "Return Delivery Result", "type": "main", "index": 0}]]},
        }
    )

    return {
        "name": "Mission Control – Business Automation",
        "nodes": intake_nodes + lead["nodes"] + delivery_nodes + hierarchy_nodes + delivery_tail,
        "connections": {
            **intake_connections,
            **lead["connections"],
            **delivery_connections,
            **hierarchy_connections,
        },
        "settings": {
            "executionOrder": "v1",
            "saveDataErrorExecution": "all",
            "saveDataSuccessExecution": "all",
            "saveManualExecutions": True,
        },
    }


def main() -> None:
    workflow = build()
    OUTPUT.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {OUTPUT.relative_to(ROOT)} with {len(workflow['nodes'])} nodes")


if __name__ == "__main__":
    main()
