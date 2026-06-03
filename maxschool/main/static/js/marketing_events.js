(function () {
    if (window.smartMarketing && window.smartMarketing.version) {
        return;
    }

    const STORAGE_KEYS = ['smartutok_lead_attribution', 'smarturok_lead_attribution'];
    const LEAD_ATTR_KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'gclid', 'fbclid', 'yclid'];
    const LEAD_EXTRA_KEYS = ['landing_path', 'referrer'];
    const LEAD_ALL_KEYS = LEAD_ATTR_KEYS.concat(LEAD_EXTRA_KEYS);

    function getConfig() {
        const cfg = window.smartMarketingConfig || {};
        const bodyPageType = document.body && document.body.dataset ? document.body.dataset.pageType : '';
        return {
            pageType: String(cfg.pageType || bodyPageType || 'unknown').trim(),
            yandexCounterId: String(cfg.yandexCounterId || '').trim(),
            hasMetaPixel: Boolean(cfg.hasMetaPixel),
        };
    }

    function sanitizeValue(value, maxLength) {
        const limit = typeof maxLength === 'number' ? maxLength : 255;
        return (value || '')
            .toString()
            .trim()
            .replace(/[\r\n]+/g, ' ')
            .slice(0, limit);
    }

    function sanitizeGoalSegment(value) {
        return (value || '')
            .toString()
            .trim()
            .toLowerCase()
            .replace(/[^a-z0-9_]+/g, '_')
            .replace(/^_+|_+$/g, '')
            .slice(0, 64);
    }

    function mapYandexGoal(eventName, payload) {
        if (eventName === 'lead_form_submit') return 'lead_form_submit';
        if (eventName === 'trial_form_submit') return 'trial_form_submit';
        if (eventName === 'trial_form_success') return 'trial_form_success';
        if (eventName === 'chat_launcher_open') return 'chat_launcher_open';
        if (eventName === 'chat_thread_open') return 'chat_thread_open';
        if (eventName === 'chat_message_send') return 'chat_message_send';
        if (eventName === 'material_view') return 'material_view';
        if (eventName === 'material_engaged') return 'material_engaged';
        if (eventName === 'material_test_submit') return 'material_test_submit';
        if (eventName === 'cta_click') {
            const ctaName = sanitizeGoalSegment(payload && payload.cta_name);
            return ctaName ? 'cta_' + ctaName : 'cta_click';
        }
        return sanitizeGoalSegment(eventName) || 'custom_event';
    }

    function readStoredAttribution() {
        for (let i = 0; i < STORAGE_KEYS.length; i += 1) {
            const key = STORAGE_KEYS[i];
            try {
                const raw = window.localStorage.getItem(key);
                if (!raw) {
                    continue;
                }
                const parsed = JSON.parse(raw);
                if (parsed && typeof parsed === 'object') {
                    return parsed;
                }
            } catch (error) {
                // Ignore malformed storage values.
            }
        }
        return {};
    }

    function saveAttribution(data) {
        const payload = JSON.stringify(data || {});
        STORAGE_KEYS.forEach(function (key) {
            try {
                window.localStorage.setItem(key, payload);
            } catch (error) {
                // Ignore private mode / storage restrictions.
            }
        });
    }

    function getAttributionFromUrl() {
        const params = new URLSearchParams(window.location.search);
        const result = {};
        LEAD_ATTR_KEYS.forEach(function (key) {
            const value = sanitizeValue(params.get(key));
            if (value) {
                result[key] = value;
            }
        });
        return result;
    }

    function buildLeadAttribution() {
        const stored = readStoredAttribution();
        const fromUrl = getAttributionFromUrl();
        const merged = Object.assign({}, stored, fromUrl);

        if (!merged.landing_path) {
            merged.landing_path = sanitizeValue(window.location.pathname + window.location.search, 500);
        }
        if (!merged.referrer) {
            merged.referrer = sanitizeValue(document.referrer, 500);
        }

        saveAttribution(merged);
        return merged;
    }

    function fillLeadFormsAttribution(attribution) {
        document.querySelectorAll('form[data-lead-form]').forEach(function (form) {
            LEAD_ALL_KEYS.forEach(function (key) {
                const input = form.querySelector('input[name="' + key + '"]');
                if (!input) {
                    return;
                }
                input.value = sanitizeValue(
                    attribution && attribution[key],
                    key === 'landing_path' || key === 'referrer' ? 500 : 255
                );
            });
        });
    }

    function track(eventName, payload) {
        const cfg = getConfig();
        const safePayload = payload && typeof payload === 'object' ? payload : {};
        const eventPayload = Object.assign(
            {
                event: eventName,
                page_type: cfg.pageType,
            },
            safePayload
        );

        window.dataLayer = window.dataLayer || [];
        window.dataLayer.push(eventPayload);

        if (typeof window.gtag === 'function') {
            window.gtag('event', eventName, eventPayload);
        }

        if (cfg.yandexCounterId && typeof window.ym === 'function') {
            window.ym(cfg.yandexCounterId, 'reachGoal', mapYandexGoal(eventName, safePayload), safePayload);
        }

        if (cfg.hasMetaPixel && typeof window.fbq === 'function') {
            if (eventName === 'lead_form_submit' || eventName === 'trial_form_submit' || eventName === 'trial_form_success') {
                window.fbq('track', 'Lead', safePayload);
            } else if (eventName === 'cta_click') {
                window.fbq('trackCustom', 'CtaClick', {
                    cta_name: safePayload.cta_name || '',
                    cta_location: safePayload.cta_location || '',
                });
            } else if (eventName === 'chat_message_send') {
                window.fbq('trackCustom', 'ChatMessageSend', safePayload);
            } else if (eventName === 'material_view') {
                window.fbq('trackCustom', 'MaterialView', safePayload);
            } else if (eventName === 'material_engaged') {
                window.fbq('trackCustom', 'MaterialEngaged', safePayload);
            } else if (eventName === 'material_test_submit') {
                window.fbq('trackCustom', 'MaterialTestSubmit', safePayload);
            } else {
                window.fbq('trackCustom', sanitizeGoalSegment(eventName) || 'custom_event', safePayload);
            }
        }

        return eventPayload;
    }

    function bindLeadForms(defaultLeadFormName) {
        const attribution = buildLeadAttribution();
        fillLeadFormsAttribution(attribution);

        document.querySelectorAll('form[data-lead-form]').forEach(function (form) {
            if (form.dataset.trackingBound === '1') {
                return;
            }
            form.dataset.trackingBound = '1';
            form.addEventListener('submit', function () {
                track('lead_form_submit', {
                    lead_form: form.dataset.leadForm || defaultLeadFormName || '',
                    utm_source: (attribution && attribution.utm_source) || '(direct)',
                });
            });
        });

        return attribution;
    }

    function bindCtas(defaultLocation) {
        document.querySelectorAll('[data-cta]').forEach(function (element) {
            if (element.dataset.ctaTrackingBound === '1') {
                return;
            }
            element.dataset.ctaTrackingBound = '1';
            element.addEventListener('click', function () {
                track('cta_click', {
                    cta_name: element.dataset.cta || '',
                    cta_location: element.dataset.ctaLocation || defaultLocation || '',
                });
            });
        });
    }

    function bindDefaults(options) {
        const opts = options && typeof options === 'object' ? options : {};
        const attribution = bindLeadForms(opts.defaultLeadFormName || '');
        bindCtas(opts.defaultCtaLocation || '');
        return attribution;
    }

    window.smartTrackEvent = track;
    window.smartMarketing = {
        version: '1.0.0',
        buildLeadAttribution: buildLeadAttribution,
        fillLeadFormsAttribution: fillLeadFormsAttribution,
        bindLeadForms: bindLeadForms,
        bindCtas: bindCtas,
        bindDefaults: bindDefaults,
        track: track,
    };
})();
