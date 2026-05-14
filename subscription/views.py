from django.shortcuts import get_object_or_404, render, redirect, reverse
from datetime import datetime
from django.utils import timezone
from rest_framework.authtoken.models import Token
from django.utils.timezone import now  
import stripe
from django.conf import settings
from imageapp.models import UserProfile
from .models import Subscription
from django.contrib.auth.models import User

stripe.api_key = settings.STRIPE_SECRET_KEY

# Create your views here.
def subscription_view(request):
    subscription = {
        'lite': 'price_1TI6lkDu2TbjVzspzETzqkBL',
        'pro': 'price_1TI6mjDu2TbjVzspWQrqp9De',
        'volume': 'price_1TI6sZDu2TbjVzspUkfwpRxF',
    }
    
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.get_full_path()}")

        price_id = request.POST.get('price_id')
        
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            payment_method_types = ['card'],
            mode = 'subscription',
            success_url = request.build_absolute_uri(reverse("create_subscription")) + f'?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url = request.build_absolute_uri(f'{reverse("subscription")}'),
            client_reference_id = request.user.id
        )
        return redirect(checkout_session.url, code = 303)
    return render(request, 'subscription.html', {'subscription': subscription})


def create_subscription(request):
    session_id = request.GET.get('session_id')

    if not session_id:
        return redirect('pricing')

    session = stripe.checkout.Session.retrieve(session_id)
    subscription_id = session.subscription

    if Subscription.objects.filter(subscription_id=subscription_id).exists():
        return redirect('my_sub')

    user = User.objects.get(id=session.client_reference_id)

    stripe_sub = stripe.Subscription.retrieve(subscription_id)

    price = stripe_sub["items"]["data"][0]["price"]
    product = stripe.Product.retrieve(price["product"])

    start_timestamp = stripe_sub["start_date"] 

    Subscription.objects.create(
        user=user,
        customer_id=session.customer,
        subscription_id=subscription_id,
        product_name=product.name,
        price=price["unit_amount"] / 100,
        interval=price["recurring"]["interval"],
        start_date=timezone.make_aware(datetime.fromtimestamp(start_timestamp)),
        is_canceled=False
    )

    profile, _ = UserProfile.objects.get_or_create(user=user)

    if price["id"] == 'price_1TI6lkDu2TbjVzspzETzqkBL':
        profile.credits_remaining += 10
    elif price["id"] == 'price_1TI6mjDu2TbjVzspWQrqp9De':
        profile.credits_remaining += 100
    elif price["id"] == 'price_1TI6sZDu2TbjVzspUkfwpRxF':
        profile.credits_remaining += 200

    profile.save()

    return redirect('my_sub')


from rest_framework.authtoken.models import Token

def my_sub_view(request):
    if not request.user.is_authenticated:
        return redirect('account_login')

    subscription = Subscription.objects.filter(user=request.user).first()
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    token, _ = Token.objects.get_or_create(user=request.user)  

    return render(request, 'my_sub.html', {
        'subscription': subscription,
        'profile': profile,
        'api_token': token.key,  
    })


def cancel_subscription(request, subscription_id):
    subscription = get_object_or_404(
        Subscription,
        user=request.user,
        subscription_id=subscription_id
    )

    stripe_sub = stripe.Subscription.modify(
        subscription_id,
        cancel_at_period_end=True
    )

    subscription.is_canceled = True
    subscription.canceled_at = now()

    end_timestamp = stripe_sub["items"]["data"][0]["current_period_end"]

    subscription.end_date = timezone.make_aware(
        datetime.fromtimestamp(end_timestamp)
    )

    subscription.save()

    return redirect('my_sub')