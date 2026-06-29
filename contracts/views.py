import io
import json
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.template.loader import get_template
from xhtml2pdf import pisa

from .models import Mission, Application, Contract, Invoice, Devis, Review
from .forms import QuickMissionForm
from .templatetags.contracts_extras import to_fcfa
User = get_user_model()


def contract_list_view(request):
    missions = Mission.objects.filter(status='open').order_by('-created_at')
    contracts = Contract.objects.all().order_by('-created_at')

    missions_data = []
    for m in missions:
        missions_data.append({
            'id': m.id,
            'title': m.title,
            'description': m.description,
            'client': m.client.username if m.client else 'Anonyme',
            'budget': float(m.budget) if m.budget is not None else None,
            'status': m.status,
            'category': m.category,
            'skills': m.tag_list,
            'urgency': m.urgency,
            'date': m.created_at.strftime('%Y-%m-%d') if m.created_at else '',
            'location': m.location,
            'duration': m.duration,
            'payment_type': m.payment_type,
            'currency': m.currency,
            'budget_type': m.budget_type,
            'budget_fcfa': to_fcfa(m.budget, m.currency) if m.budget is not None else None,
            'budget_display': m.budget_display,
            'extra_info': m.extra_info or '',
        })

    return render(request, 'contracts/contract_list.html', {
        'missions_json': missions_data,
        'missions': missions,
        'contracts': contracts,
    })


def freelance_list_api(request):
    freelances = User.objects.filter(role='FREELANCE').values('id', 'username', 'email')
    return JsonResponse({
        "status": "success",
        "freelances": list(freelances)
    })


def mission_list_api(request):
    missions = Mission.objects.all().order_by('-created_at').values(
        'id', 'title', 'description', 'budget', 'skills_required'
    )
    return JsonResponse({
        "status": "success",
        "total_missions": missions.count(),
        "missions": list(missions)
    })


def tarifs_api(request):
    grille_tarifs = {
        "Développeur Junior": "15,000 - 30,000 CFA/jour",
        "Développeur Mid-level": "40,000 - 75,000 CFA/jour",
        "Expert / Senior": "150,000+ CFA/jour",
        "DevOps / Cloud": "100,000+ CFA/jour"
    }
    return JsonResponse({
        "status": "success",
        "devise": "CFA",
        "grille": grille_tarifs
    })


@login_required
def create_contract_view(request):
    if hasattr(request.user, 'role') and request.user.role != 'CLIENT':
        messages.error(request, "Seuls les profils Clients peuvent publier des offres.")
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = QuickMissionForm(request.POST)
        if form.is_valid():
            mission = form.save(commit=False)
            mission.client = request.user
            mission.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Mission publiée avec succès !'})
            messages.success(request, "Mission publiée avec succès !")
    return redirect('contracts:contract_list')


@login_required
def invoice_view(request):
    if hasattr(request.user, 'role') and request.user.role != 'FREELANCE':
        messages.error(request, "Seuls les freelances peuvent gérer des factures.")
        return redirect('accounts:dashboard')

    user = request.user
    profile = getattr(user, 'freelance_profile', None)

    if request.method == 'POST':
        action = request.POST.get('action')

        # ── CRÉER ──
        if action == 'create':
            try:
                from django.utils import timezone
                import json
                
                invoice = Invoice(
                    freelance=user,
                    client_name=request.POST.get('client_name', '').strip(),
                    client_email=request.POST.get('client_email', '').strip(),
                    client_company=request.POST.get('client_company', '').strip(),
                    client_address=request.POST.get('client_address', '').strip(),
                    client_phone=request.POST.get('client_phone', '').strip(),
                    description=request.POST.get('description', '').strip(),
                    amount=float(request.POST.get('amount', 0)),
                    tva=float(request.POST.get('tva', 18)),
                    freelance_company=request.POST.get('freelance_company', '').strip(),
                    freelance_address=request.POST.get('freelance_address', '').strip(),
                    freelance_phone=request.POST.get('freelance_phone', '').strip(),
                    freelance_siret=request.POST.get('freelance_siret', '').strip(),
                    issue_date=request.POST.get('issue_date') or timezone.now().date(),
                    due_date=request.POST.get('due_date') or timezone.now().date(),
                    terms=request.POST.get('terms', '').strip() or 'Paiement à réception sous 30 jours',
                    notes=request.POST.get('notes', '').strip(),
                    bank_name=request.POST.get('bank_name', '').strip(),
                    bank_iban=request.POST.get('bank_iban', '').strip(),
                    bank_bic=request.POST.get('bank_bic', '').strip(),
                    status=request.POST.get('status', 'draft'),
                )
                invoice.save()

                mission_id = request.POST.get('mission_id')
                if mission_id:
                    try:
                        invoice.mission = Mission.objects.get(id=mission_id)
                        invoice.save()
                    except (Mission.DoesNotExist, ValueError):
                        pass

                application_id = request.POST.get('application_id')
                if application_id:
                    try:
                        invoice.application = Application.objects.get(id=application_id)
                        invoice.save()
                    except (Application.DoesNotExist, ValueError):
                        pass

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success', 'message': 'Facture créée avec succès !', 'invoice': {
                        'id': invoice.id, 'ref': invoice.ref
                    }})
                messages.success(request, f'Facture {invoice.ref} créée avec succès !')
            except (ValueError, TypeError) as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': f'Erreur : {str(e)}'}, status=400)
                messages.error(request, f'Erreur : {str(e)}')
            return redirect('contracts:invoices')

        # ── MODIFIER ──
        elif action == 'update':
            invoice_id = request.POST.get('invoice_id')
            try:
                invoice = Invoice.objects.get(id=invoice_id, freelance=user)
                invoice.client_name = request.POST.get('client_name', invoice.client_name)
                invoice.client_email = request.POST.get('client_email', invoice.client_email)
                invoice.client_company = request.POST.get('client_company', invoice.client_company)
                invoice.client_address = request.POST.get('client_address', invoice.client_address)
                invoice.client_phone = request.POST.get('client_phone', invoice.client_phone)
                invoice.description = request.POST.get('description', invoice.description)
                invoice.amount = float(request.POST.get('amount', invoice.amount))
                invoice.tva = float(request.POST.get('tva', invoice.tva))
                invoice.freelance_company = request.POST.get('freelance_company', invoice.freelance_company)
                invoice.freelance_address = request.POST.get('freelance_address', invoice.freelance_address)
                invoice.freelance_phone = request.POST.get('freelance_phone', invoice.freelance_phone)
                invoice.freelance_siret = request.POST.get('freelance_siret', invoice.freelance_siret)
                issue_date = request.POST.get('issue_date')
                if issue_date:
                    invoice.issue_date = issue_date
                due_date = request.POST.get('due_date')
                if due_date:
                    invoice.due_date = due_date
                invoice.terms = request.POST.get('terms', invoice.terms)
                invoice.notes = request.POST.get('notes', invoice.notes)
                invoice.bank_name = request.POST.get('bank_name', invoice.bank_name)
                invoice.bank_iban = request.POST.get('bank_iban', invoice.bank_iban)
                invoice.bank_bic = request.POST.get('bank_bic', invoice.bank_bic)
                invoice.status = request.POST.get('status', invoice.status)
                invoice.save()

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success', 'message': 'Facture mise à jour avec succès !'})
                messages.success(request, f'Facture {invoice.ref} mise à jour.')
            except Invoice.DoesNotExist:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'Facture introuvable.'}, status=404)
                messages.error(request, 'Facture introuvable.')
            return redirect('contracts:invoices')

        # ── SUPPRIMER ──
        elif action == 'delete':
            invoice_id = request.POST.get('invoice_id')
            try:
                invoice = Invoice.objects.get(id=invoice_id, freelance=user)
                ref = invoice.ref
                invoice.delete()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success', 'message': f'Facture {ref} supprimée.'})
                messages.success(request, f'Facture {ref} supprimée.')
            except Invoice.DoesNotExist:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'Facture introuvable.'}, status=404)
                messages.error(request, 'Facture introuvable.')
            return redirect('contracts:invoices')

    # ── GET ──
    invoices = Invoice.objects.filter(freelance=user)

    missions = Mission.objects.filter(status__in=['open', 'in-progress']).order_by('-created_at')
    applications = Application.objects.filter(freelance=user, status='pending').select_related('mission')

    total_count = invoices.count()
    paid_count = invoices.filter(status='paid').count()
    sent_count = invoices.filter(status='sent').count()
    overdue_count = invoices.filter(status='overdue').count()
    total_revenue = sum(i.total_ttc for i in invoices.filter(status='paid'))

    invoices_json = []
    for inv in invoices:
        invoices_json.append({
            'id': inv.id,
            'ref': inv.ref,
            'client_name': inv.client_name,
            'client_email': inv.client_email,
            'client_company': inv.client_company,
            'description': inv.description,
            'amount': float(inv.amount),
            'tva': float(inv.tva),
            'total_ttc': inv.total_ttc,
            'status': inv.status,
            'issue_date': inv.issue_date.strftime('%Y-%m-%d') if inv.issue_date else '',
            'due_date': inv.due_date.strftime('%Y-%m-%d') if inv.due_date else '',
            'notes': inv.notes or '',
            'freelance_company': inv.freelance_company,
        })

    return render(request, 'contracts/invoices.html', {
        'invoices': invoices,
        'invoices_json': invoices_json,
        'missions': missions,
        'applications': applications,
        'total_count': total_count,
        'paid_count': paid_count,
        'sent_count': sent_count,
        'overdue_count': overdue_count,
        'total_revenue': total_revenue,
        'profile': profile,
    })


@login_required
def invoice_pdf_view(request, invoice_id):
    user = request.user
    inv = get_object_or_404(Invoice, id=invoice_id)
    if user != inv.freelance and user.role != 'ADMIN':
        if inv.client_email != user.email:
            messages.error(request, "Accès refusé.")
            return redirect('accounts:dashboard')

    template = get_template('contracts/invoice_pdf.html')
    html = template.render({'inv': inv, 'user': user})

    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('UTF-8')), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{inv.ref}.pdf"'
        return response
    return HttpResponse('Erreur lors de la génération du PDF', status=500)


# ── DEVIS ──

@login_required
def devis_view(request):
    user = request.user
    profile = getattr(user, 'freelance_profile', None)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            if user.role != 'FREELANCE':
                return JsonResponse({'status': 'error', 'message': 'Seuls les freelances peuvent créer des devis.'}, status=403)
            try:
                from django.utils import timezone
                devis = Devis(
                    freelance=user,
                    client_name=request.POST.get('client_name', '').strip(),
                    client_email=request.POST.get('client_email', '').strip(),
                    client_company=request.POST.get('client_company', '').strip(),
                    client_phone=request.POST.get('client_phone', '').strip(),
                    description=request.POST.get('description', '').strip(),
                    amount=float(request.POST.get('amount', 0)),
                    tva=float(request.POST.get('tva', 18)),
                    freelance_company=request.POST.get('freelance_company', '').strip(),
                    freelance_phone=request.POST.get('freelance_phone', '').strip(),
                    freelance_address=request.POST.get('freelance_address', '').strip(),
                    freelance_siret=request.POST.get('freelance_siret', '').strip(),
                    issue_date=request.POST.get('issue_date') or timezone.now().date(),
                    valid_until=request.POST.get('valid_until') or None,
                    terms=request.POST.get('terms', '').strip() or 'Devis valable 30 jours',
                    notes=request.POST.get('notes', '').strip(),
                    status=request.POST.get('status', 'draft'),
                )
                client_id = request.POST.get('client_id')
                if client_id:
                    try:
                        devis.client = User.objects.get(id=client_id)
                    except (User.DoesNotExist, ValueError):
                        pass
                devis.save()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success', 'message': 'Devis créé avec succès !'})
                messages.success(request, f'Devis {devis.ref} créé !')
            except (ValueError, TypeError) as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': f'Erreur : {str(e)}'}, status=400)
                messages.error(request, f'Erreur : {str(e)}')
            return redirect('contracts:devis')

        elif action == 'update':
            devis_id = request.POST.get('devis_id')
            try:
                devis = Devis.objects.get(id=devis_id, freelance=user)
                devis.client_name = request.POST.get('client_name', devis.client_name)
                devis.client_email = request.POST.get('client_email', devis.client_email)
                devis.client_company = request.POST.get('client_company', devis.client_company)
                devis.client_phone = request.POST.get('client_phone', devis.client_phone)
                devis.description = request.POST.get('description', devis.description)
                devis.amount = float(request.POST.get('amount', devis.amount))
                devis.tva = float(request.POST.get('tva', devis.tva))
                devis.freelance_company = request.POST.get('freelance_company', devis.freelance_company)
                devis.freelance_phone = request.POST.get('freelance_phone', devis.freelance_phone)
                devis.freelance_address = request.POST.get('freelance_address', devis.freelance_address)
                devis.freelance_siret = request.POST.get('freelance_siret', devis.freelance_siret)
                issue = request.POST.get('issue_date')
                if issue:
                    devis.issue_date = issue
                valid = request.POST.get('valid_until')
                if valid:
                    devis.valid_until = valid
                devis.terms = request.POST.get('terms', devis.terms)
                devis.notes = request.POST.get('notes', devis.notes)
                devis.status = request.POST.get('status', devis.status)
                devis.save()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success', 'message': 'Devis mis à jour !'})
                messages.success(request, f'Devis {devis.ref} mis à jour.')
            except Devis.DoesNotExist:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'Devis introuvable.'}, status=404)
                messages.error(request, 'Devis introuvable.')
            return redirect('contracts:devis')

        elif action == 'delete':
            devis_id = request.POST.get('devis_id')
            try:
                devis = Devis.objects.get(id=devis_id, freelance=user)
                ref = devis.ref
                devis.delete()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success', 'message': f'Devis {ref} supprimé.'})
                messages.success(request, f'Devis {ref} supprimé.')
            except Devis.DoesNotExist:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'Devis introuvable.'}, status=404)
                messages.error(request, 'Devis introuvable.')
            return redirect('contracts:devis')

    # GET
    if user.role == 'FREELANCE':
        devis_list = Devis.objects.filter(freelance=user)
    elif user.role == 'CLIENT':
        devis_list = Devis.objects.filter(client=user)
    else:
        devis_list = Devis.objects.none()

    total_count = devis_list.count()
    sent_count = devis_list.filter(status='sent').count()
    accepted_count = devis_list.filter(status='accepted').count()

    devis_json = []
    for d in devis_list:
        devis_json.append({
            'id': d.id,
            'ref': d.ref,
            'client_name': d.client_name,
            'client_email': d.client_email,
            'client_company': d.client_company,
            'description': d.description,
            'amount': float(d.amount),
            'tva': float(d.tva),
            'total_ttc': d.total_ttc,
            'status': d.status,
            'issue_date': d.issue_date.strftime('%Y-%m-%d') if d.issue_date else '',
            'valid_until': d.valid_until.strftime('%Y-%m-%d') if d.valid_until else '',
            'freelance_company': d.freelance_company,
        })

    clients = User.objects.filter(role='CLIENT') if user.role == 'FREELANCE' else []

    return render(request, 'contracts/devis.html', {
        'devis_list': devis_list,
        'devis_json': devis_json,
        'total_count': total_count,
        'sent_count': sent_count,
        'accepted_count': accepted_count,
        'profile': profile,
        'clients': clients,
    })


@login_required
def devis_pdf_view(request, devis_id):
    user = request.user
    devis = get_object_or_404(Devis, id=devis_id)
    if user != devis.freelance and user != devis.client and user.role != 'ADMIN':
        messages.error(request, "Accès refusé.")
        return redirect('accounts:dashboard')

    template = get_template('contracts/devis_pdf.html')
    html = template.render({'devis': devis, 'user': user})

    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('UTF-8')), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{devis.ref}.pdf"'
        return response
    return HttpResponse('Erreur lors de la génération du PDF', status=500)


@login_required
def client_invoices_view(request):
    user = request.user
    if user.role != 'CLIENT':
        messages.error(request, "Accès réservé aux clients.")
        return redirect('accounts:dashboard')

    invoices = Invoice.objects.filter(client_email=user.email).order_by('-created_at')

    return render(request, 'contracts/client_invoices.html', {
        'invoices': invoices,
    })


def mission_detail_view(request, pk):
    mission = get_object_or_404(Mission, pk=pk)

    user = request.user
    unread_count = 0
    if user.is_authenticated:
        from chat.models import Thread, Message
        if user.role == User.Role.FREELANCE.value:
            user_threads = user.freelance_threads.all()
        else:
            user_threads = user.client_threads.all()
        unread_count = sum(
            t.messages.filter(is_read=False).exclude(sender=user).count()
            for t in user_threads
        )

    return render(request, 'contracts/mission_detail.html', {
        'mission': mission,
        'unread_count': unread_count,
    })


@login_required
def apply_to_mission_view(request, mission_id):
    mission = get_object_or_404(Mission, id=mission_id)

    if mission.status != 'open':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Cette mission n\'est plus ouverte aux candidatures.'})
        messages.error(request, "Cette mission n'est plus ouverte aux candidatures.")
        return redirect('contracts:mission_list')

    if hasattr(request.user, 'role') and request.user.role != 'FREELANCE':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Seuls les freelances peuvent postuler.'})
        messages.error(request, "Seuls les profils Freelances peuvent postuler aux offres.")
        return redirect('accounts:home')

    if mission.client == request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Vous ne pouvez pas postuler à votre propre mission.'})
        messages.error(request, "Vous ne pouvez pas postuler à votre propre mission.")
        return redirect('accounts:home')

    # Vérification que le freelance est approuvé par l'admin
    if not (hasattr(request.user, 'freelance_profile') and request.user.freelance_profile.is_verified):
        try:
            from chat.models import Thread, Message
            admin = User.objects.filter(is_superuser=True, is_staff=True).first()
            if admin:
                if admin.role == User.Role.FREELANCE.value:
                    thread, _ = Thread.objects.get_or_create(client=request.user, freelance=admin)
                else:
                    thread, _ = Thread.objects.get_or_create(client=admin, freelance=request.user)
                Message.objects.create(
                    thread=thread,
                    sender=admin,
                    text=f"Bonjour {request.user.username}, votre compte freelance est en cours de validation "
                         f"par l'administration. Veuillez attendre d'être vérifié avant de postuler aux missions."
                )
        except Exception:
            pass
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Votre compte doit être vérifié par l\'administration avant de pouvoir postuler.'})
        messages.error(request, "Votre compte doit être vérifié par l'administration avant de pouvoir postuler.")
        return redirect('accounts:home')

    proposed_rate = request.POST.get('proposed_rate') or request.GET.get('proposed_rate')

    if mission.budget_type == 'negotiable' and not proposed_rate:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Veuillez proposer un tarif pour cette mission (budget à discuter).', 'need_rate': True})
        messages.error(request, "Veuillez proposer un tarif pour cette mission (budget à discuter).")
        return redirect('contracts:contract_list')

    already_applied = Application.objects.filter(mission=mission, freelance=request.user).exists()
    if already_applied:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'warning', 'message': 'Vous avez déjà postulé.'})
        messages.warning(request, "Vous avez déjà candidaté à cette offre.")
    else:
        app = Application(mission=mission, freelance=request.user)
        if proposed_rate:
            try:
                app.proposed_rate = float(proposed_rate)
            except (ValueError, TypeError):
                pass
        app.save()

        # Messages automatiques si le freelance est vérifié
        try:
            if (hasattr(request.user, 'freelance_profile') and
                request.user.freelance_profile.is_verified):

                from chat.models import Thread, Message

                thread, _ = Thread.objects.get_or_create(
                    client=mission.client,
                    freelance=request.user
                )

                profile = request.user.freelance_profile
                skills = ', '.join(profile.skill_list[:5]) if profile.skill_list else 'Non renseignées'

                # Message du freelance au client
                Message.objects.create(
                    thread=thread,
                    sender=request.user,
                    text=f"Bonjour, je viens de postuler à votre mission « {mission.title} ». "
                         f"Voici mon profil : {request.user.username} | {profile.title or 'Freelance'} "
                         f"({to_fcfa(profile.hourly_rate, 'EUR'):,.0f} FCFA/h) — Compétences : {skills}. "
                         f"N'hésitez pas à me contacter pour plus d'informations."
                )

                # Message de confirmation au freelance
                Message.objects.create(
                    thread=thread,
                    sender=mission.client,
                    text=f"Bonjour {request.user.username}, votre candidature pour la mission "
                         f"« {mission.title} » a bien été reçue. Le client vous recontactera "
                         f"si votre profil est retenu."
                )
        except Exception:
            pass  # Ne pas bloquer la candidature si l'envoi automatique échoue

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': 'Candidature envoyée !'})
        messages.success(request, f"Candidature envoyée pour '{mission.title}' !")

    return redirect('contracts:contract_list')


def _update_freelance_rating(freelance_user):
    """Recalcule la note moyenne du freelance à partir de ses Review."""
    from django.db.models import Avg
    from accounts.models import FreelanceProfile
    avg = Review.objects.filter(freelance=freelance_user).aggregate(Avg('rating'))['rating__avg']
    profile = getattr(freelance_user, 'freelance_profile', None)
    if profile:
        profile.rating = round(avg, 1) if avg else 0.0
        profile.save(update_fields=['rating'])


@login_required
def submit_review_view(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée.'}, status=405)

    if request.user.role != 'CLIENT':
        return JsonResponse({'status': 'error', 'message': 'Seuls les clients peuvent noter.'}, status=403)

    freelance_id = request.POST.get('freelance_id')
    mission_id = request.POST.get('mission_id')
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '').strip()

    if not all([freelance_id, mission_id, rating]):
        return JsonResponse({'status': 'error', 'message': 'Champs requis manquants.'}, status=400)

    try:
        freelance = User.objects.get(id=freelance_id, role='FREELANCE')
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Freelance introuvable.'}, status=404)

    try:
        rating_val = int(rating)
        if rating_val < 1 or rating_val > 5:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'La note doit être entre 1 et 5.'}, status=400)

    mission = get_object_or_404(Mission, id=mission_id, client=request.user)

    if mission.status != 'closed':
        return JsonResponse({'status': 'error', 'message': 'La mission doit être terminée pour pouvoir noter.'}, status=400)

    has_accepted = mission.applications.filter(freelance=freelance, status='accepted').exists()
    if not has_accepted:
        return JsonResponse({'status': 'error', 'message': 'Ce freelance n\'a pas travaillé sur cette mission.'}, status=400)

    review, created = Review.objects.update_or_create(
        client=request.user,
        freelance=freelance,
        mission=mission,
        defaults={'rating': rating_val, 'comment': comment},
    )

    _update_freelance_rating(freelance)

    return JsonResponse({
        'status': 'success',
        'message': 'Note enregistrée !' if created else 'Note mise à jour !',
        'review': {
            'id': review.id,
            'rating': review.rating,
            'comment': review.comment,
        },
    })

