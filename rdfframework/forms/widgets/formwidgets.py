__author__ = "Mike Stabile, Jeremy Nelson"

from wtforms.widgets import HTMLString, html_params
from wtforms.compat import text_type
from rdfframework.utilities import is_not_null
class BsGridTableWidget(object):
    """
    Renders a list of fields as a bootstrap formated table.

    If `with_row_tag` is True, then an enclosing <row> is placed around the
    rows.

    Hidden fields will not be displayed with a row, instead the field will be
    pushed into a subsequent table row to ensure XHTML validity. Hidden fields
    at the end of the field list will appear outside the table.
    """
    def __init__(self, with_section_tag=False):
        self.with_section_tag = with_section_tag

    def __call__(self, field, **kwargs):
        html = []
        if self.with_section_tag:
            kwargs.setdefault('id', field.id)
            html.append('<section class="col-md-6" %s>' % html_params(**kwargs))
        hidden = ''
        _params = html_params(**kwargs)
        for subfield in field:
            if subfield.type == 'CSRFTokenField':
                html.append('<div style="display:none" %s>%s</div>' % (_params,text_type(subfield(class_="form-control"))))
            else:
                html.append('<div class="col-md-2" %s>%s</div>' % (_params,text_type(subfield(class_="form-control"))))
                hidden = ''
        if self.with_section_tag:
            html.append('</section>')
        if hidden:
            html.append(hidden)
        return HTMLString(''.join(html))
DEBUG = False
class RepeatingSubFormWidget(object):
    """
    Renders a list of fields as a `row` list.

    This is used for fields which encapsulate many inner fields as subfields.
    The widget will try to iterate the field to get access to the subfields and
    call them to render them.

    If `prefix_label` is set, the subfield's label is printed before the field,
    otherwise afterwards. The latter is useful for iterating radios or
    checkboxes.
    """
    def __init__(self, html_tag='div', prefix_label=True):
        assert html_tag in ('ol', 'ul', 'div', 'section')
        self.html_tag = html_tag
        self.prefix_label = prefix_label

    def __call__(self, field, **kwargs):
        if DEBUG:
            debug = True
        else:
            debug = False
        if debug: print("START RepeatingSubFormWidget.call ---------------\n")
        kwargs.setdefault('id', field.id)
        _params = html_params(**kwargs)
        html = []
        html.append("<div id='%s_form' class='repeating-subform'>" % field.name)
        html.append('<%s class="row visible-lg visible-md">' % (self.html_tag))
        display_mode = False
        if field[0].form.instance_uri == "kdr_DisplayForm":
            display_mode = True
        for fld in field[0].form.rdf_field_list:
            flag_str = ""
            label = ""
            if fld.flags.required and not display_mode:
                flag_str = " *"
            if fld.type not in ['CSRFTokenField', 'HiddenField']:
                label = fld.label
            html.append('''
                <section class="col-md-2">
                    <div class="form-group">
                        %s%s
                    </div>
                </section>''' % (label, flag_str))
        html.append('</%s>' % (self.html_tag))
        row = 0   
        for subfield in field:
            html.append('<%s class="row subform-row">' % self.html_tag)
            html.append(subfield.form.hidden_tag())
            if debug: print("row ",row)
            row +=1
            for fld in subfield.form.rdf_field_list:
                if debug: print(fld.name)
                error_css = ""
                error_msg = ""
                error_list = []
                if fld.type == 'HiddenField':
                    continue
                if display_mode:
                    if fld.kds_formFieldName.endswith("_image"):
                        data = '<img src="/badges/fedora_image?id=%s" style="height:50px">' \
                                % fld.data.replace("<","").replace(">","")
                    elif hasattr(fld, "selected_display"):
                        data = fld.selected_display
                    else:
                        data = fld.data
                    if hasattr(fld, "kds_call_in_display"):
                        fld_render = fld(id=fld.name,
                                         class_=fld.kds_css,
                                         readonly=not fld.editable)
                    else:
                        fld_render = \
                                '<div id="%s" class="form-control-static">%s</div>' % \
                                (fld.name, data)
                else:
                    fld_render = fld(id=fld.name,
                                     class_=fld.kds_css,
                                     readonly=not fld.editable)
                if fld.errors:
                    error_css = " has-error"
                    error_msg = "<ul class='help-block'><li>%s</li></ul>" % \
                            "</li><li>".join(fld.errors)
                html.append('''
                    <section class="col-md-2">
                        <div class="form-group %s">
                            %s
                            %s
                            %s
                        </div>
                    </section>''' % (error_css,
                                     fld.label(class_="control-label visible-sm visible-xs"),
                                     fld_render,
                                     error_msg))
            html.append('</%s>' % self.html_tag)
        html.append('</div>')
        if debug: print(HTMLString(''.join(html)))
        if debug: print("\nEND RepeatingSubFormWidget.call ---------------\n")
        return HTMLString(''.join(html))

class RepeatingSubFormTableJinga2Widget(object):
    """
    Renders a list of fields as a `row` list.

    This is used for fields which encapsulate many inner fields as subfields.
    The widget will try to iterate the field to get access to the subfields and
    call them to render them.

    If `prefix_label` is set, the subfield's label is printed before the field,
    otherwise afterwards. The latter is useful for iterating radios or
    checkboxes.
    """
    def __init__(self, html_tag='div', prefix_label=True):
        assert html_tag in ('ol', 'ul', 'div')
        self.html_tag = html_tag
        self.prefix_label = prefix_label

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        _params = html_params(**kwargs)
        html = []
        html.append('<%s class="row">' % (self.html_tag))
        for sub_subfield in field[0]:
            if sub_subfield.type != 'CSRFTokenField':
                html.append('<div class="col-md-2">%s</div>' % sub_subfield.label)
        html.append('</%s>' % (self.html_tag))    
        for subfield in field:
            html.append('<%s class="row">%s</%s>' % (self.html_tag,
                                           #_params,
                                           subfield(),
                                           self.html_tag))
        return HTMLString(''.join(html))
        
class ButtonActionWidget(object):
    ''' This widget will place a button on the page that will call a function
        as passed in '''
        
    def __call__(self, field, **kwargs):
        if hasattr(field,'kds_buttonAction'):
            button_action = field.kds_buttonAction
        else:
            button_action = ''
        if hasattr(field,'kds_buttonText'):
            button_text = field.kds_buttonText
        else:
            button_text = 	{'false': 'Click', 'true': 'Resend'}
        if hasattr(field,'kds_buttonLink'):
            button_link = field.kds_buttonLink
        else:
            button_link = ''
        if hasattr(field,'kds_buttonFalseCss'):
            button_true_css = field.kds_buttonFalseCss
        else:
            button_true_css = 'btn-success'
        if hasattr(field,'kds_buttonTrueCss'):
            button_false_css = field.kds_buttonTrueCss
        else:
            button_false_css = 'btn-danger'
        button_action = kwargs.get('button_action', button_action)
        button_text = kwargs.get('button_text', button_text)
        button_link = kwargs.get('button_link', button_link)
        css = kwargs.pop('class', '') or kwargs.pop('class_', '')
        if is_not_null(field.data):
            css = "%s %s" % (css, button_true_css)
        else:
            css = "%s %s" % (css, button_false_css)
        if button_action[:-2] == "()":
            button_action = button_action[:-2]
        return_args = []
        return_args.append("<a ")
        if is_not_null(field.data):
            button_text = button_text['true']
        else:
            button_text = button_text['false']
        if is_not_null(button_action):
            return_args.append("href='javascript:;' ")
            return_args.append('onclick="%s(\'%s\',this,\'%s\',\'%s\')" ' % 
                    (button_action, field.data, button_false_css, \
                     button_true_css))
        else:
            return_args.append("href='%s' " % button_link)
        return_args.append("class='%s' " % css)
        return_args.append("kds_propUri='%s' " % field.kds_propUri)
        return_args.append("kds_classUri='%s' " % field.kds_classUri)
        return_args.append("kds_errorLogPropUri='%s' " % \
                           field.kds_errorLogPropUri)
        return_args.append("data=\"%s\" " % field.data)
        return_args.append("id='%s' " % field.name)
        return_args.append(">%s</a>" % button_text)
        return "".join(return_args)