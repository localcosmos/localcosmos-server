from django.template.defaultfilters import slugify

def create_unique_slug(initial_str, field, Model, max_len=50):

    slug_base = slugify(initial_str)[:max_len-1]

    # if many special characters are used, do not transliterate, simply use the unicode expression
    if len(slug_base) == 0:
        slug_base = initial_str

    slug = slug_base

    exists = Model.objects.filter(**{field:slug}).exists()

    i = 2
    while exists:
        
        if len(slug) > max_len:
            slug_base = slug_base[:-1]
            
        slug = '%s%s' % (slug_base, i)
        i += 1
        exists = Model.objects.filter(**{field:slug}).exists()

    return slug
