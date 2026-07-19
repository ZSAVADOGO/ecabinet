from django import template

register = template.Library()

@register.filter(name='replace_underscore')
def replace_underscore(value):
    if not value:
        return ""
    return str(value).replace('_', ' ')
