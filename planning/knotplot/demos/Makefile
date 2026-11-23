zoo:
	.make-backup

cisr:
	find * -newer cisr.time -prune -print -exec zoo -add cisr.zoo {} \;
	mv cisr.zoo $(HOME)/scratch/cisr.zoo
	echo " " > cisr.time



math:
	find * -newer math.time -prune -print -exec zoo -add math.zoo {} \;
	mv math.zoo $(HOME)/scratch/math.zoo
	echo " " > math.time

clean:
	/bin/rm *dum* *~

