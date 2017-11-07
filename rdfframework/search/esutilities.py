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