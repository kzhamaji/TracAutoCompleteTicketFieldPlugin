// vim: ts=8:sts=2:sw=2:et
(function($) {
  $(function() {

    function get_url (tail) {
      start = $('link[rel="start"]').attr('href');
      elems = start.split('/');
      elems.pop();
      elems.push(tail);
      return elems.join('/');
    }

    function split (val) {
      return val.split(/[,\s]\s*/);
    }
    function extractLast (term) {
      return split(term).pop();
    }

    function source_function_for_multi (source) {
      return function ( req, res ) {
        res($.ui.autocomplete.filter(source, extractLast(req.term)));
      }
    }

    function find_field_name (dom) {
        name = $(dom).attr('id') || $(dom).attr('name')
        return name.replace('field-', '')
                   .replace(/^\d+_/, '')
                   .replace('batchmod_value_', '');
    }

    function enable_autocomplete ( options ) {

      $('input.autocomplticketfield').each(function(){
        name = find_field_name(this);
        $(this).autocomplete({
          autoFocus: true,
          source: options[name],
        });
      });

      $('input.autocomplticketfield-multi').each(function(){
        name = find_field_name(this);
        $(this).bind("keydown", function( event ) {
          if (event.keyCode === $.ui.keyCode.TAB &&
              $(this).autocomplete("instance").menu.active ) {
            event.preventDefault();
          }
        })
        .autocomplete({
          autoFocus: true,
          source: source_function_for_multi(options[name]),
          focus: function( event, ui ) {
            return false;
          },
          select: function( event, ui ) {
            var terms = split(this.value);
            var sep = this.value.indexOf(',') < 0 ? ' ' : ', ';
            terms.pop();
            terms.push(ui.item.value);
            this.value = terms.join(sep);
            return false;
          },
        })
        .blur(function(){
          this.value = this.value.replace(/,?\s*$/, '');
        });
      });
    }

    function enable_observe (options, sflds, mflds, target, input_pfx, input) {

      targets = $(target)
      if ( targets[0] ) {
        $.each(sflds, function(i,fld){
          selector = input_pfx + fld + ' ' + input;
          targets.observe('added', selector, function( record ) {
            $(this).addClass('autocomplticketfield');
            enable_autocomplete(options);
          });
        });
        $.each(mflds, function(i,fld){
          selector = input_pfx + fld + ' ' + input;
          targets.observe('added', selector, function( record ) {
            $(this).addClass('autocomplticketfield-multi');
            enable_autocomplete(options);
          });
        });
      }
    }


    $.getJSON(get_url('ticketfield_completion'), function(json) {
      options = json.options
      sflds = json.single;
      mflds = json.multi;

      enable_autocomplete(options);

      enable_observe(options, sflds.concat(mflds), [],
                    '#query #filters table.trac-clause',
                    'tbody tr.', 'td.filter input');
      enable_observe(options, sflds, mflds,
                    '#batchmod_fieldset table tbody',
                    'tr#batchmod_', 'input');
    });

  });
})(jQuery);
