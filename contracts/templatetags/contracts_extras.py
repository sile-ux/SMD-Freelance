from django import template

register = template.Library()


@register.filter
def intcomma(value):
    try:
        s = str(int(value))
        groups = []
        while s and s[-1].isdigit():
            groups.append(s[-3:])
            s = s[:-3]
        groups.reverse()
        return s + ','.join(groups)
    except (ValueError, TypeError):
        return value
