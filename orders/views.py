from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from carts.models import CartItem
from .forms import OrderForm
from .models import Order, OrderProduct, Payment
import datetime
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from store.models import Product

# payment stripe
import stripe
from django.conf import settings

# Email
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site


stripe.api_key = settings.STRIPE_SECRET_KEY
# DOMAIN = settings.DOMAIN
# Create your views here.


def CreateCheckoutSessionView(request):
    return


def charge(request):
    if request.method == 'POST':
        charge = stripe.Charge.create(
            amount=1000,
            currency='idr',
            description='desccc',
            source=request.POST['stripeToken']
        )
        return render(request, 'payment_success.html')


@login_required(login_url='login')
def payments(request, order_number):
    current_user = request.user
    YOURDOMAIN = f"{request.scheme}://{request.get_host()}"

    order = Order.objects.get(
        user=current_user, is_ordered=False, order_number=order_number)

    # cart = get_object_or_404(Order, id=order_id)
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    grand_total = 0
    tax = 0
    total = 0
    quantity = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity

    tax = (2 * total)/100
    grand_total = total + tax
    try:
        print("mulaaaaaaaaaaaiiiiiiiiiii")
        check_out_session = stripe.checkout.Session.create(
            payment_method_types=['card'],

            line_items=[
                {
                    'price_data': {
                        'currency': 'USD',
                        'product_data': {'name': 'xxx'},
                        'unit_amount': 1100
                    },
                    'quantity': quantity

                }
            ],

            mode='payment',
            success_url=YOURDOMAIN +
            f"/orders/payments-success?session_id={{CHECKOUT_SESSION_ID}}&order_number={order_number}",
            # cancel_url='http://localhost:8000/payments-failed'
            # success_url=YOURDOMAIN +'/orders/payments-success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=YOURDOMAIN + '/orders/payments-failed/'


        )
        session = check_out_session.id
        # print("sessiiionnnn", session)
        # return JsonResponse({"checkout_url": check_out_session.url})
        return redirect(check_out_session.url)

    except stripe.error.StripeError as e:
        # JsonResponse({"error": str(e)}, status=400)
        print("error nya", e)
        return HttpResponse("error cuiiii", str(e))

    # return render(request, 'orders/payments.html')


@login_required(login_url='login')
def payments_success(request):
    current_user = request.user
    session_id = request.GET.get("session_id")
    order_number = request.GET.get("order_number")
    order = Order.objects.get(
        user=current_user, is_ordered=False, order_number=order_number)

    # donation_id = request.GET.get("donation_id")
    # print("order number", request.GET.get("order_number"))

    if not session_id:  # or not dontation_id
        return JsonResponse({"error": "Invalid session"}, status=400)

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        # print("SESSION", session)
        # donation = get_object_or_404(Donation, id = donation_id)
        print("session status", session.payment_status)
        if session.payment_status == 'paid':
            payment = Payment(
                user=current_user,
                payment_id=session.payment_intent,
                payment_method='Stripe',
                amount_paid=session.amount_total/100,
                status='Completed'

            )
            payment.save()

            order.payment = payment
            order.is_ordered = True
            order.status = 'Completed'
            order.save()

            # move the card item into order product
            cart_items = CartItem.objects.filter(user=request.user)
            for item in cart_items:
                orderproduct = OrderProduct()
                orderproduct.order_id = order.id
                orderproduct.payment = payment
                orderproduct.user = request.user
                orderproduct.product_id = item.product_id
                orderproduct.quantity = item.quantity
                orderproduct.product_price = item.product.price
                orderproduct.ordered = True
                orderproduct.save()

                cart_item = CartItem.objects.get(id=item.id)
                product_variation = cart_item.variations.all()
                orderproduct = OrderProduct.objects.get(id=orderproduct.id)
                orderproduct.variations.set(product_variation)
                orderproduct.save()

            # reduce the quantity of the sold products
                product = Product.objects.get(id=item.product_id)
                product.stock -= item.quantity
                product.save()

            # clear the cart
            CartItem.objects.filter(user=request.user).delete()

            # send email to customer

            mail_subject = 'Thank you for your order'
            message = render_to_string('orders/order_received_email.html', {
                'user': current_user,
                'order': order,
            })

            to_email = request.user.email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()

            # send order number and transaction id to invoice
            orderproduct = OrderProduct.objects.filter(order_id=order.id)
            subtotal = 0
            grandtotal = 0
            for i in orderproduct:
                subtotal += (i.quantity * i.product_price)

            grandtotal = subtotal + order.tax

            context = {
                'order': order,
                'orderproduct': orderproduct,
                'subtotal': subtotal,
                'grandtotal': grandtotal
            }

            return render(request, 'orders/payment_success.html', context)

        return JsonResponse({"error": "payment not completed"}, status=400)
    except stripe.error.StripeError as e:
        return JsonResponse({"error": str(e)}, status=400)


def payments_failed(request):
    error_message = request.GET.get(
        "error", "Your payment could not be processed. Please try again")
    return render(request, "orders/payment_failed.html", {'error_message': error_message})


def place_order(request, total=0, quantity=0):
    current_user = request.user

    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()

    if cart_count <= 0:
        return redirect('store')
    else:
        pass

    grand_total = 0
    tax = 0

    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity

    tax = (2 * total)/100
    grand_total = total + tax

    if request.method == 'POST':
        form = OrderForm(request.POST)

        if form.is_valid():
            data = Order()
            data.user = request.user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()

            # generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr, mt, dt)
            current_date = d.strftime('%Y%m%d')
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            order = Order.objects.get(
                user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total
            }
            return render(request, 'orders/payments.html', context)
        else:
            return redirect('checkout')
