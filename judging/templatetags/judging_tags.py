from django import template

register = template.Library()


@register.filter
def dictkeystr(d, key):
    """Look up a dict value by key (converting key to int for integer dict keys)."""
    if not isinstance(d, dict):
        return ''
    try:
        return d.get(int(key), d.get(key, ''))
    except (ValueError, TypeError):
        return d.get(key, '')
