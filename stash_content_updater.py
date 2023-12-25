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

    # Verifica se a resposta é bem-sucedida (código 200)
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

def find_performers(model_name):
    query = '''
        query {
          findPerformers (
            performer_filter: {
              name: {
                value: "%s",
                modifier: EQUALS
              }
            }
          ) {
            performers {
              id,
              name,
              alias_list
            }
          }
        }
    ''' % model_name

    extract_data_func = lambda response: response.get('data', {}).get('findPerformers', {}).get('performers', [])
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

    print(query)
    extract_data_func = lambda response: response.get('data', {}).get(f'find{query_type}', {})
    return execute_query(make_graphql_request, {'query': query}, extract_data_func)

def bulk_update_items(item_type, item_ids, performer_id):
    ids_str = ", ".join(map(str, item_ids))
    query_bulk_update = f'''
        mutation {{
          bulk{item_type}Update(
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

    extract_data_func = lambda response: response.get('data', {}).get(f'bulk{item_type}Update', {})
    return execute_query(make_graphql_request, {'query': query_bulk_update}, extract_data_func)

def process_folders(base_folder):
    sub_folders = [folder for folder in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, folder))]

    for sub_folder in sub_folders:
        try:
            response_performer = find_performers(sub_folder)
            performers = response_performer

            if not performers:
                continue

            performer_id = performers[0]["id"]
            performer_name = performers[0]["name"]

            response_images = find_media('Images', performer_name)
            image_count = response_images.get("count", 0)

            if image_count == 0:
                continue

            image_ids = [image["id"] for image in response_images.get('images', [])]

            bulk_update_items('Image', image_ids, performer_id)

            response_scenes = find_media('Scenes', performer_name)
            scene_count = response_scenes.get("count", 0)

            if scene_count == 0:
                continue

            scene_ids = [scene["id"] for scene in response_scenes.get('scenes', [])]

            bulk_update_items('Scene', scene_ids, performer_id)

        except Exception as e:
            logging.error(f"Error processing folder {sub_folder}: {str(e)}")

base_folder = "/volumes/Documents/Testing/Exclusive Content"

process_folders(base_folder)
