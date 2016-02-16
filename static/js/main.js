
$(document).ready(function() {

    $( "#textMeForm" ).submit(function( event ) {

      event.preventDefault();

      var $form = $( this ),
        number = $form.find( "input[name='phone']" ).val();

      var posting = $.post( 'https://justyo.co/textme', {
          number: number,
          username: $('input#username').val(),
          app_id: 'co.justyo.yostatus',
      } );

      posting.done(function( data ) {
          $('#addbutton').show(); $('#textMeForm').hide();
      });
    });

});

