"""Reusable deterministic policy decision engine for cooperating gateways."""
import ipaddress

APP_DOMAINS = {
    'youtube': ['youtube.com', 'youtu.be', 'googlevideo.com', 'ytimg.com'],
    'instagram': ['instagram.com', 'cdninstagram.com'],
    'facebook': ['facebook.com', 'fbcdn.net', 'messenger.com'],
    'tiktok': ['tiktok.com', 'tiktokcdn.com', 'byteoversea.com'],
    'netflix': ['netflix.com', 'nflxvideo.net', 'nflximg.net'],
    'discord': ['discord.com', 'discord.gg', 'discordapp.com'],
    'whatsapp': ['whatsapp.com', 'whatsapp.net'],
    'telegram': ['telegram.org', 't.me'],
    'roblox': ['roblox.com', 'rbxcdn.com'],
    'steam': ['steampowered.com', 'steamcommunity.com', 'steamstatic.com'],
    'spotify': ['spotify.com', 'scdn.co', 'spotifycdn.com'],
    'reddit': ['reddit.com', 'redd.it', 'redditmedia.com', 'redditstatic.com'],
    'snapchat': ['snapchat.com', 'sc-cdn.net', 'snapkit.com'],
    'pinterest': ['pinterest.com', 'pinimg.com'],
    'twitch': ['twitch.tv', 'ttvnw.net', 'jtvnw.net'],
}


def matches(kind, target, *, mac='', ip='', domain='', app=''):
    value = target.lower().strip()
    if kind == 'device':
        return bool(mac) and mac.lower().replace('-', ':') == value.replace('-', ':')
    if kind == 'ip':
        try:
            return bool(ip) and ipaddress.ip_address(ip) in ipaddress.ip_network(value, strict=False)
        except ValueError:
            return False
    if kind == 'domain':
        d = domain.lower().split(':')[0].strip('. ')
        t = value.split(':')[0].strip('. ')
        return bool(d) and (d == t or d.endswith('.' + t))
    if kind == 'app':
        if app and app.lower() == value:
            return True
        return any(matches('domain', item, domain=domain) for item in APP_DOMAINS.get(value, []))
    return False


def decide(rules, *, mac='', ip='', domain='', app='', user_id=None, device_id=None, device_blocked=False):
    if device_blocked:
        return {'allowed': False, 'reason': 'Device blocked by administrator', 'policy_id': None}
    ranked = []
    for rule in rules:
        if not rule['enabled']:
            continue
        scope = rule['scope_type']
        if scope == 'user' and (user_id is None or rule['scope_id'] != user_id):
            continue
        if scope == 'device' and (device_id is None or rule['scope_id'] != device_id):
            continue
        if not matches(rule['kind'], rule['target'], mac=mac, ip=ip, domain=domain, app=app):
            continue
        # Scoped policy wins over global. At equal scope, explicit block wins.
        priority = (1 if scope != 'all' else 0, 1 if rule['action'] == 'block' else 0)
        ranked.append((priority, rule))
    if not ranked:
        return {'allowed': True, 'reason': 'No matching restriction', 'policy_id': None}
    rule = max(ranked, key=lambda x: x[0])[1]
    return {'allowed': rule['action'] == 'allow', 'reason': f"Policy: {rule['name']}", 'policy_id': rule['id']}
