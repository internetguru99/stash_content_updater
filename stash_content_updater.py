import os
import requests

def make_graphql_request(query, variables=None):
    url = "http://10.0.0.25:9999/graphql"
    headers = {"Content-Type": "application/json"}
    payload = {"query": query, "variables": variables}
    response = requests.post(url, headers=headers, json=payload)
    return response.json()

def find_performers(model_name):
    query_performer = f'''
        query {{
          findPerformers (
            performer_filter: {{
              name: {{
                value: "{model_name}",
                modifier: EQUALS
              }}
            }}
          ) {{
            performers {{
              id,
              name,
              alias_list
            }}
          }}
        }}
    '''
    return make_graphql_request(query_performer)

def find_images(performer_name):
    query_images = f'''
        query {{
          findImages (
            image_filter: {{
              path: {{
                value: "Z:Testing\\\\Exclusive Content\\\\{performer_name}\\\\",
                modifier: INCLUDES
              }}
            }}
          ) {{
            count,
            images {{
              id,
              studio {{
                id,
                name,
                parent_studio {{
                  id,
                  name
                }},
                scene_count,
                image_count,
              }},
              tags {{
                id,
                name,
                description,
                parents {{
                	id,
                  name
                }}, 
                image_count
              }}
            }}
          }}
        }}
    '''

    return make_graphql_request(query_images)

def bulk_update_images(image_ids, performer_id):
    ids_str = ", ".join(map(str, image_ids))
    query_bulk_update = f'''
        mutation {{
          bulkImageUpdate(
            input: {{
              ids: [{ids_str}],
              performer_ids: {{
                mode: ADD,
                ids: [{performer_id}]
              }}
            }}
          ) {{
            id,
            title,
            date
          }}
        }}
    '''

    print(query_bulk_update)
    return make_graphql_request(query_bulk_update)

def process_folders(base_folder):
    sub_folders = [folder for folder in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, folder))]

    for sub_folder in sub_folders:
        response_performer = find_performers(sub_folder)
        performers = response_performer.get("data", {}).get("findPerformers", {}).get("performers", [])

        if not performers:
            continue

        performer_id = performers[0]["id"]
        performer_name = performers[0]["name"]

        response_images = find_images(performer_name)
        image_count = response_images.get("data", {}).get("findImages", {}).get("count", 0)

        if image_count == 0:
            continue

        image_ids = [image["id"] for image in response_images["data"]["findImages"]["images"]]

        bulk_update_images(image_ids, performer_id)

base_folder = "/volumes/Documents/Testing/Exclusive Content"

process_folders(base_folder)
