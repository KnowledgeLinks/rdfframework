def get_es_action_item(data_item, action_settings, es_type, id_field=None):
    ''' This method will return an item formated and ready to append
        to the action list '''

    action_item = dict.copy(action_settings)
    if id_field is not None:
        id_val = first(list(get_dict_key(data_item, id_field)))
        if id_val is not None:
            action_item['_id'] = id_val
    elif data_item.get('id'):
        if data_item['id'].startswith("%s/" % action_settings['_index']):
            action_item['_id'] = "/".join(data_item['id'].split("/")[2:])
        else:
            action_item['_id'] = data_item['id']
    if data_item.get('data'):
        action_item['_source'] = data_item['data']
    else:
        action_item['_source'] = data_item
    action_item['_type'] = es_type
    return action_item

def mapping_ref(es_url):
    es_mappings = \
            json.loads(requests.get('{0}:9200/_mapping'.format(es_url)).text)
    es_mappings = {"_".join(key.split("_")[:-1]): value['mappings'] \
                   for key, value in es_mappings.items()}

    new_map = {}
    for key, value in es_mappings.items():
        for sub_key, sub_value in value.items():
            new_map["/".join([key, sub_key])] = mapping_fields(sub_value['properties'
            ])
    return new_map

def mapping_fields(mapping, parent=[]):
    # rtn_list = []
    # for key, value in mapping.items():
    #     new_key = parent + [key]
    #     new_key = ".".join(new_key)
    #     rtn_list.append((new_key, value.get('type')))
    #     if value.get('properties'):
    #         rtn_list += mapping_fields(value['properties'], [new_key])
    #     elif value.get('fields'):
    #         rtn_list += mapping_fields(value['fields'], [new_key])
    # return rtn_list
    rtn_obj = {}
    for key, value in mapping.items():
        new_key = parent + [key]
        new_key = ".".join(new_key)
        rtn_obj.update({new_key: value.get('type')})
        if value.get('properties'):
            rtn_obj.update(mapping_fields(value['properties'], [new_key]))
        elif value.get('fields'):
            rtn_obj.update(mapping_fields(value['fields'], [new_key]))
            rtn_obj[new_key] = [rtn_obj[new_key]] + list(value['fields'].keys())
    return rtn_obj

def key_data_map(source, mapping, parent=[]):
    rtn_obj = {}
    if isinstance(source, dict):
        for key, value in source.items():

            new_key = parent + [key]
            new_key = ".".join(new_key)
            rtn_obj.update({new_key: {'mapping':mapping.get(new_key)}})
            if isinstance(value, list):
                value = value[0]
                rtn_obj.update(key_data_map(value, mapping, [new_key]))
                if isinstance(value, dict):
                    rtn_obj[new_key]['data'] = "%s ...}" % str(value)[:60]
            elif isinstance(value, dict):
                rtn_obj.update(key_data_map(value, mapping, [new_key]))
                rtn_obj[new_key]['data'] = "%s ...}" % str(value)[:60]
            else:
                rtn_obj[new_key]['data'] = value
    elif isinstance(source, list):
        rtn_obj.update(key_data_map(value[0], mapping, parent))
    else:
        rtn_obj = {"".join(parent): {'data':source,
                                     'mapping':mapping.get("".join(parent))}}
        # pdb.set_trace()
    return rtn_obj

def sample_data_convert(es_url, data, es_index, doc_type):
    maps = mapping_ref(es_url)
    if data.get('hits'):
        new_data = data['hits']['hits'][0]['_source']
    elif data.get('_source'):
        new_data = data['_source']
    conv_data = key_data_map(new_data, maps["%s/%s" % (es_index, doc_type)])
    conv_data = [(key, str(value['mapping']), str(value['data']),) \
                 for key, value in conv_data.items()]
    conv_data.sort(key=lambda tup: es_field_sort(tup[0]))
    return conv_data

def sample_data_map(es_url):

    maps = mapping_ref(es_url)
    rtn_obj = {}
    for path, mapping in maps.items():
        url = "/".join(["{}:9200".format(es_url), path, '_search'])
        sample_data = json.loads(requests.get(url).text)
        sample_data = sample_data['hits']['hits'][0]['_source']
        conv_data = key_data_map(sample_data, mapping)

        rtn_obj[path] = [(key, str(value['mapping']), str(value['data']),) \
                         for key, value in conv_data.items()]
        rtn_obj[path].sort(key=lambda tup: es_field_sort(tup[0]))
    return rtn_obj

def es_field_sort(fld_name):
    """ Used with lambda to sort fields """
    parts = fld_name.split(".")
    if "_" not in parts[-1]:
        parts[-1] = "_" + parts[-1]
    return ".".join(parts)
