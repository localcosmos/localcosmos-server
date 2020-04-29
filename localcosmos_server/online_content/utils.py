def verbosify_template_name(template_name):
    verbose_name = ' '.join(template_name.replace('.html','').split('/')[-1].split('_')).capitalize()

    return verbose_name
