$(function(){
	prettyPrint();

	$('.prettyprintExpand').click(function(){
		if($(this).next().hasClass('expanded')){
			$(this).text('Expand').next().removeClass('expanded');
		}
		else{
			$(this).text('Collapse').next().addClass('expanded');
		}
	});

	if( $('#homepageDemo').length ){
		$('#homepageDemo').jsVideoPlayer({
			showTitle:false,
			showVolumeControl:false
		});
		$('.clicktoplay, .clicktoreplay').click(function(){
			$('#homepageDemo .jsvp-control-play').click();
		});
	}

	$('.shareWrap .fb').click(function(){
		fbShare();
	});
	$('.shareWrap .tt').click(function(){
		twitter();
	});
	$('.shareWrap .li').click(function(){
		linkedIn();
	});
	$('.shareWrap .gp').click(function(){
		googlePlus();
	});

	$('.sendMail').attr('href','mailto:info@uiplayground.in').text('info@uiplayground.in');
});

var shareText = 'An image based player with customizable effects/animation, with a look an feel of a Video Player, simple visit www.uiplayground.in/jquery-image-player/ ';
function twitter() {
	window.open('http://twitter.com/share?text='+shareText, 'sharer', 'toolbar=0,status=0,width=626,height=436');
}
function googlePlus(){
	window.open('http://twitter.com/share?text='+shareText, 'sharer', 'toolbar=0,status=0,width=626,height=436');
}
function fbShare(){
	var title = document.title;
	var url = location.href;
	var summary = shareText;
	var image = "http://www.uiplayground.in/css3-icons/images/logo.png";
	var openwin = decodeURI('http://www.facebook.com/sharer.php?s=100&p[title]=' + title + '&p[summary]=' + summary + '&p[url]=' + url + '&p[images][0]=' + image + '');
	window.open(openwin, '', 'width=626,height=436');
}
function linkedIn(){
	var location = window.location;
	var title = document.title;
	var summary = shareText;
	var PageLink = "http://www.linkedin.com/shareArticle?mini=true&url="+location+"&title="+title+"&summary="+summary+"&source=''";
	newwindow=window.open(PageLink,'uiplayground.in | css3icons','height=350,width=626');
	if (window.focus) {newwindow.focus()}
	return false;
}





