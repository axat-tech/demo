class AccountAuthView(RegisterUserMixin, generic.TemplateView):
    template_name = 'customer/login_registration.html'
    login_prefix, registration_prefix = 'login', 'registration'
    login_form_class = EmailAuthenticationForm
    registration_form_class = EmailUserCreationForm
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super(AccountAuthView, self).get(
            request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        ctx = super(AccountAuthView, self).get_context_data(*args, **kwargs)
        if 'login_form' not in kwargs:
            ctx['login_form'] = self.get_login_form()
        if 'registration_form' not in kwargs:
            ctx['registration_form'] = self.get_registration_form()
        return ctx

    def post(self, request, *args, **kwargs):
        # Use the name of the submit button to determine which form to validate
        if u'login_submit' in request.POST:
            if request.is_ajax():
                return self.validate_login_form_ajax()
            else:
                return self.validate_login_form()
        elif u'registration_submit' in request.POST:
            return self.validate_registration_form()
        return http.HttpResponseBadRequest()

    # LOGIN

    def get_login_form(self, bind_data=False):
        return self.login_form_class(
            **self.get_login_form_kwargs(bind_data))

    def get_login_form_kwargs(self, bind_data=False):
        kwargs = {'host': self.request.get_host(), 'prefix': self.login_prefix, 'initial': {
            'redirect_url': self.request.GET.get(self.redirect_field_name, ''),
        }}
        if bind_data and self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def validate_login_form_ajax(self):
        form = self.get_login_form(bind_data=True)
        if form.is_valid():
            user = form.get_user()

            # Grab a reference to the session ID before logging in
            old_session_key = self.request.session.session_key

            auth_login(self.request, form.get_user())

            # Raise signal robustly (we don't want exceptions to crash the
            # request handling). We use a custom signal as we want to track the
            # session key before calling login (which cycles the session ID).
            signals.user_logged_in.send_robust(
                sender=self, request=self.request, user=user,
                old_session_key=old_session_key)

            msg = self.get_login_success_message(form)
            if msg:
                messages.success(self.request, msg)

            redirect_url = self.request.POST.get('redirect_url', '')

            if len(redirect_url) == 0:
                redirect_url = self.get_login_success_url(form)

            return HttpResponse(
                json.dumps({
                    "success": True,
                    'redirect_url': redirect_url
                }),
                content_type="application/json"
            )
        else:
            user_errors = dict(form.errors.items())
            return HttpResponse(
                json.dumps({
                    "success": False,
                    "message": user_errors
                }),
                content_type="application/json"
            )

    def validate_login_form(self):
        form = self.get_login_form(bind_data=True)
        if form.is_valid():
            user = form.get_user()

            # Grab a reference to the session ID before logging in
            old_session_key = self.request.session.session_key

            auth_login(self.request, form.get_user())

            # Raise signal robustly (we don't want exceptions to crash the
            # request handling). We use a custom signal as we want to track the
            # session key before calling login (which cycles the session ID).
            signals.user_logged_in.send_robust(
                sender=self, request=self.request, user=user,
                old_session_key=old_session_key)

            msg = self.get_login_success_message(form)
            if msg:
                messages.success(self.request, msg)

            return redirect(self.get_login_success_url(form))

        ctx = self.get_context_data(login_form=form)
        return self.render_to_response(ctx)

    def get_login_success_message(self, form):
        return _("Welcome back")

    def get_login_success_url(self, form):
        redirect_url = form.cleaned_data['redirect_url']
        if redirect_url:
            return redirect_url

        # Redirect staff members to dashboard as that's the most likely place
        # they'll want to visit if they're logging in.
        if self.request.user.is_staff:
            return reverse('dashboard:index')

        if self.request.user.is_employee:
            return reverse('company:employee:index')

        return settings.LOGIN_REDIRECT_URL

    # REGISTRATION
    def get_registration_form(self, bind_data=False):
        return self.registration_form_class(
            **self.get_registration_form_kwargs(bind_data))

    def get_registration_form_kwargs(self, bind_data=False):
        kwargs = {'host': self.request.get_host(), 'prefix': self.registration_prefix, 'initial': {
            'redirect_url': self.request.GET.get(self.redirect_field_name, ''),
        }}
        if bind_data and self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def validate_registration_form(self):
        form = self.get_registration_form(bind_data=True)
        if form.is_valid():
            self.register_user(form)

            msg = self.get_registration_success_message(form)
            messages.success(self.request, msg)

            return redirect(self.get_registration_success_url(form))

        ctx = self.get_context_data(registration_form=form)
        return self.render_to_response(ctx)

    def get_registration_success_message(self, form):
        return _("Thanks for signing up!")

    def get_registration_success_url(self, form):
        return settings.LOGIN_REDIRECT_URL