import os
import requests
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def make_graphql_request(query, variables=None):
    url = "http://10.0.0.25:9999/graphql"
    headers = {"Content-Type": "application/json"}
    payload = {"query": query, "variables": variables}
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"GraphQL request failed with status code {response.status_code}")
        return {}

def execute_query(query_func, query_params, extract_data_func):
    try:
        response = query_func(**query_params)
        return extract_data_func(response)
    except Exception as e:
        logging.error(f"Error executing query {query_func.__name__}: {str(e)}")
        return {}

def find_entities(query_type):
    common_fields = '''
        id,
        name,
        scene_count,
        image_count
    '''

    performer_fields = '''
        gender,
        birthdate,
        country,
        alias_list,
        tags {
            name
        }
    '''

    query = f'''
        query {{
          find{query_type} (
            filter: {{
              per_page: -1
            }}
          )
          {{
            {query_type.lower()} {{
              {common_fields}
              {''.join([performer_fields] if query_type.lower() == 'performers' else [])}
            }}
          }}
        }}
    '''

    extract_data_func = lambda response: response.get('data', {}).get(f'find{query_type}', {}).get(query_type.lower(), [])
    return execute_query(make_graphql_request, {'query': query}, extract_data_func)

def find_media(query_type, performer_name):
    query = f'''
        query {{
          find{query_type} (
            {query_type.rstrip("s").lower()}_filter: {{
              path: {{
                value: "Z:Testing\\\\Exclusive Content\\\\{performer_name}\\\\",
                modifier: INCLUDES
              }}
            }},
              filter: {{
                per_page: -1
              }}
          ) {{
            count,
            {query_type.lower()} {{
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

    extract_data_func = lambda response: response.get('data', {}).get(f'find{query_type}', {}).get(query_type.lower(), [])
    return execute_query(make_graphql_request, {'query': query}, extract_data_func)

def bulk_update_items(item_type, item_ids, performer_id, studio_id):
    ids_str = ", ".join(map(str, item_ids))
    query_bulk_update = f'''
        mutation {{
          bulk{item_type}Update(
            input: {{
              ids: [{ids_str}],
              performer_ids: {{
                mode: ADD,
                ids: [{performer_id}]
              }},
              studio_id: {studio_id}
            }}
          ) {{
            id,
            title,
            date
          }}
        }}
    '''

    extract_data_func = lambda response: response.get('data', {}).get(f'bulk{item_type}Update', {})
    return execute_query(make_graphql_request, {'query': query_bulk_update}, extract_data_func)

def process_folders(base_folder):
    sub_folders = [folder for folder in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, folder))]

    try:
        response_performers = find_entities("Performers")
        performers = response_performers

        if not performers:
            logging.info("No performers found.")
            return

        response_studios = find_entities("Studios")
        studios = response_studios

        if not studios:
            logging.info("No studios found.")
            return

        for sub_folder in sub_folders:
            performer_id = None
            studio_id = None

            for performer in performers:
                if sub_folder == performer["name"] or sub_folder in performer["alias_list"]:
                    performer_id = performer["id"]
                    break

            if performer_id is None:
                logging.info(f"No matching performer found for folder {sub_folder}.")
                continue

            base_folder_name = os.path.basename(os.path.normpath(base_folder))

            for studio in studios:
                if base_folder_name == studio["name"]:
                    studio_id = studio["id"]
                    break

            if studio_id is None:
                logging.info(f"No matching studio found for folder {sub_folder}.")
                continue

            response_images = find_media('Images', performer["name"])

            if len(response_images) > 0:
                image_ids = [image["id"] for image in response_images]
                bulk_update_items('Image', image_ids, performer_id, studio_id)

            response_scenes = find_media('Scenes', performer["name"])

            if len(response_studios) > 0:
                scene_ids = [scene["id"] for scene in response_scenes]
                bulk_update_items('Scene', scene_ids, performer_id, studio_id)

    except Exception as e:
        logging.error(f"Error processing folders: {str(e)}")

base_folder = "S:\\Content Creators\\Exclusive Content"
process_folders(base_folder)
