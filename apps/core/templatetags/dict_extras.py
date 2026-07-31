from django import template

register = template.Library()


@register.filter
def get_item(dictionnaire, cle):
    """
    Permet {{ mon_dict|get_item:ma_variable_cle }} dans un template,
    ce que Django ne supporte pas nativement (seul {{ mon_dict.cle_litterale }} fonctionne).
    """
    if not dictionnaire:
        return None
    return dictionnaire.get(cle)