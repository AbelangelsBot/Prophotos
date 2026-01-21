"""
Validation des emails pour bloquer les domaines jetables/temporaires.
Inclut verification MX et SMTP basique.
"""

import re
import dns.resolver
import smtplib
import socket
import logging

logger = logging.getLogger(__name__)

# Liste des domaines email jetables les plus courants
DISPOSABLE_EMAIL_DOMAINS = {
    # Services de mail temporaire populaires
    "tempmail.com", "temp-mail.org", "temp-mail.io",
    "10minutemail.com", "10minutemail.net", "10minmail.com",
    "guerrillamail.com", "guerrillamail.org", "guerrillamail.net", "guerrillamail.biz",
    "mailinator.com", "mailinator.net", "mailinator.org",
    "throwaway.email", "throwawaymail.com",
    "fakeinbox.com", "fakemailgenerator.com",
    "getnada.com", "nada.email",
    "dispostable.com",
    "mailnesia.com",
    "maildrop.cc",
    "mintemail.com",
    "mohmal.com",
    "tempail.com",
    "tempr.email",
    "discard.email",
    "discardmail.com",
    "spamgourmet.com",
    "trashmail.com", "trashmail.net", "trashmail.org",
    "yopmail.com", "yopmail.fr", "yopmail.net",
    "sharklasers.com",
    "spam4.me",
    "grr.la",
    "guerrillamailblock.com",
    "pokemail.net",
    "emailondeck.com",
    "tempmailaddress.com",
    "burnermail.io",
    "inboxalias.com",
    "jetable.org",
    "mailcatch.com",
    "mailexpire.com",
    "mailforspam.com",
    "meltmail.com",
    "mt2009.com",
    "mytrashmail.com",
    "nobulk.com",
    "noclickemail.com",
    "nogmailspam.info",
    "nomail.xl.cx",
    "nowmymail.com",
    "spambox.us",
    "spamfree24.org",
    "spamherelots.com",
    "spamobox.com",
    "tempomail.fr",
    "tmpmail.net",
    "tmpmail.org",
    "wegwerfmail.de",
    "wegwerfmail.net",
    "wegwerfmail.org",
    "zoemail.org",
    "mailnull.com",
    "e4ward.com",
    "spamex.com",
    "emailsensei.com",
    "incognitomail.com", "incognitomail.net", "incognitomail.org",
    "mailslite.com",
    "33mail.com",
    "amilegit.com",
    "anonymbox.com",
    "antispam.de",
    "binkmail.com",
    "bobmail.info",
    "burnthespam.info",
    "buyusedlibrarybooks.org",
    "byom.de",
    "deadaddress.com",
    "despam.it",
    "devnullmail.com",
    "dfgh.net",
    "dodgeit.com",
    "dodgemail.de",
    "dontreg.com",
    "dontsendmespam.de",
    "dump-email.info",
    "dumpyemail.com",
    "e-mail.com",
    "e-mail.org",
    "emailgo.de",
    "emailias.com",
    "emailmiser.com",
    "emailto.de",
    "emailwarden.com",
    "emz.net",
    "enterto.com",
    "ephemail.net",
    "etranquil.com",
    "etranquil.net",
    "etranquil.org",
    "evopo.com",
    "explodemail.com",
    "fastacura.com",
    "fastchevy.com",
    "fastchrysler.com",
    "fastkawasaki.com",
    "fastmazda.com",
    "fastmitsubishi.com",
    "fastnissan.com",
    "fastsubaru.com",
    "fastsuzuki.com",
    "fasttoyota.com",
    "fastyamaha.com",
    "filzmail.com",
    "fizmail.com",
    "flyspam.com",
    "gawab.com",
    "getonemail.com",
    "getonemail.net",
    "girlsundertheinfluence.com",
    "gishpuppy.com",
    "great-host.in",
    "gsrv.co.uk",
    "haltospam.com",
    "hidzz.com",
    "hotpop.com",
    "ieatspam.eu",
    "ieatspam.info",
    "ihateyoualot.info",
    "imails.info",
    "inboxclean.com",
    "inboxclean.org",
    "incognitomail.com",
    "instantemailaddress.com",
    "ipoo.org",
    "irish2me.com",
    "jetable.com",
    "jetable.fr.nf",
    "jetable.net",
    "jnxjn.com",
    "junk1.com",
    "kasmail.com",
    "kaspop.com",
    "keepmymail.com",
    "killmail.com",
    "killmail.net",
    "klassmaster.com",
    "klassmaster.net",
    "kulturbetrieb.info",
    "kurzepost.de",
    "lawlita.com",
    "letthemeatspam.com",
    "lhsdv.com",
    "lifebyfood.com",
    "link2mail.net",
    "litedrop.com",
    "lol.ovpn.to",
    "lookugly.com",
    "lopl.co.cc",
    "lortemail.dk",
    "lovemeleaveme.com",
    "lr78.com",
    "maboard.com",
    "mail-hierarchyis-admin.cf",
    "mail-hierarchyis-admin.ga",
    "mail-hierarchyis-admin.gq",
    "mail-hierarchyis-admin.ml",
    "mail-hierarchyis-admin.tk",
    "mail-temp.com",
    "mail.by",
    "mail.mezimages.net",
    "mail2rss.org",
    "mail333.com",
    "mail4trash.com",
    "mailbidon.com",
    "mailblocks.com",
    "mailfreeonline.com",
    "mailguard.me",
    "mailin8r.com",
    "mailinater.com",
    "mailismagic.com",
    "mailmate.com",
    "mailme.ir",
    "mailme.lv",
    "mailmetrash.com",
    "mailmoat.com",
    "mailnator.com",
    "mailsac.com",
    "mailscrap.com",
    "mailseal.de",
    "mailshell.com",
    "mailsiphon.com",
    "mailtemp.info",
    "mailtothis.com",
    "mailzilla.com",
    "mailzilla.org",
}

# Pattern pour valider le format basique d'un email
EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)


def is_valid_email_format(email):
    """
    Verifie si le format de l'email est valide.
    """
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email))


def is_disposable_email(email):
    """
    Verifie si l'email utilise un domaine jetable.
    Retourne True si c'est un email jetable (a bloquer).
    """
    if not email:
        return True

    try:
        domain = email.lower().split('@')[1]
        return domain in DISPOSABLE_EMAIL_DOMAINS
    except (IndexError, AttributeError):
        return True


def validate_email(email):
    """
    Valide un email completement.
    Retourne (is_valid, error_message).
    """
    if not email:
        return False, "Email requis."

    email = email.strip().lower()

    if not is_valid_email_format(email):
        return False, "Format d'email invalide."

    if is_disposable_email(email):
        return False, "Les emails temporaires/jetables ne sont pas acceptes."

    return True, None


def get_domain(email):
    """
    Extrait le domaine d'un email.
    """
    try:
        return email.lower().split('@')[1]
    except (IndexError, AttributeError):
        return None


def check_mx_record(domain):
    """
    Verifie si le domaine a des enregistrements MX (serveur mail).
    Retourne (has_mx, mx_hosts) ou (False, None) si erreur.
    """
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_hosts = [str(r.exchange).rstrip('.') for r in mx_records]
        return True, mx_hosts
    except dns.resolver.NoAnswer:
        # Pas d'enregistrement MX, essayer l'enregistrement A
        try:
            dns.resolver.resolve(domain, 'A')
            return True, [domain]
        except Exception:
            return False, None
    except dns.resolver.NXDOMAIN:
        # Domaine n'existe pas
        return False, None
    except dns.resolver.Timeout:
        # Timeout - on laisse passer par prudence
        logger.warning(f"DNS timeout for domain: {domain}")
        return True, None
    except Exception as e:
        logger.warning(f"DNS error for {domain}: {e}")
        return True, None  # En cas d'erreur, on laisse passer


def verify_email_smtp(email, mx_hosts, timeout=5):
    """
    Verification SMTP basique - tente de verifier si l'email existe.

    ATTENTION: Cette methode n'est pas fiable a 100%:
    - Gmail/Outlook acceptent toutes les adresses au niveau SMTP
    - Certains serveurs bloquent ces verifications

    Retourne (is_valid, message)
    """
    if not mx_hosts:
        return True, None  # Pas de MX connu, on laisse passer

    local_part = email.split('@')[0]
    domain = email.split('@')[1]

    for mx_host in mx_hosts[:2]:  # Essayer les 2 premiers MX
        try:
            # Connexion au serveur SMTP
            smtp = smtplib.SMTP(timeout=timeout)
            smtp.connect(mx_host, 25)
            smtp.helo('prophotos.local')
            smtp.mail('verify@prophotos.local')

            # Verifier si le destinataire est accepte
            code, message = smtp.rcpt(email)
            smtp.quit()

            if code == 250:
                return True, None  # Email accepte
            elif code == 550:
                return False, "Cette adresse email n'existe pas."
            elif code == 551 or code == 552 or code == 553:
                return False, "Cette adresse email est invalide."
            else:
                # Code inconnu, on laisse passer
                return True, None

        except smtplib.SMTPServerDisconnected:
            continue
        except smtplib.SMTPConnectError:
            continue
        except socket.timeout:
            continue
        except socket.gaierror:
            continue
        except Exception as e:
            logger.warning(f"SMTP verification error for {email}: {e}")
            continue

    # Si on n'a pas pu verifier, on laisse passer
    return True, None


def verify_email_exists(email):
    """
    Verification complete de l'existence d'un email:
    1. Verifie les enregistrements MX du domaine
    2. Tente une verification SMTP (si possible)

    Retourne (is_valid, error_message)
    """
    domain = get_domain(email)
    if not domain:
        return False, "Format d'email invalide."

    # 1. Verifier les enregistrements MX
    has_mx, mx_hosts = check_mx_record(domain)
    if not has_mx:
        return False, f"Le domaine '{domain}' n'a pas de serveur mail configure."

    # 2. Verification SMTP (optionnelle, peut etre lente)
    # Desactiver pour les gros domaines connus qui acceptent tout
    skip_smtp_domains = {
        'gmail.com', 'googlemail.com',
        'outlook.com', 'hotmail.com', 'live.com', 'msn.com',
        'yahoo.com', 'yahoo.fr',
        'icloud.com', 'me.com', 'mac.com',
        'protonmail.com', 'proton.me',
        'aol.com',
    }

    if domain.lower() not in skip_smtp_domains:
        is_valid, error_msg = verify_email_smtp(email, mx_hosts)
        if not is_valid:
            return False, error_msg

    return True, None


def validate_email(email, check_exists=True):
    """
    Valide un email completement.
    Retourne (is_valid, error_message).

    Args:
        email: L'adresse email a valider
        check_exists: Si True, verifie aussi que l'email existe (MX + SMTP)
    """
    if not email:
        return False, "Email requis."

    email = email.strip().lower()

    if not is_valid_email_format(email):
        return False, "Format d'email invalide."

    if is_disposable_email(email):
        return False, "Les emails temporaires/jetables ne sont pas acceptes."

    # Verification de l'existence de l'email (MX + SMTP)
    if check_exists:
        exists, error_msg = verify_email_exists(email)
        if not exists:
            return False, error_msg

    return True, None
