from django import template

register = template.Library()

CURRENCY_RATES = {
    'EUR': 656,
    'USD': 600,
    'GBP': 760,
    'XOF': 1,
}


def to_fcfa(amount, currency='XOF'):
    rate = CURRENCY_RATES.get(currency, 1)
    return float(amount) * rate


@register.filter
def fcfa(amount, currency='XOF'):
    try:
        value = to_fcfa(amount, currency)
        return '{:,.0f} FCFA'.format(value).replace(',', ' ')
    except (ValueError, TypeError):
        return str(amount)


@register.filter
def fcfa_value(amount, currency='XOF'):
    try:
        return to_fcfa(amount, currency)
    except (ValueError, TypeError):
        return 0


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
