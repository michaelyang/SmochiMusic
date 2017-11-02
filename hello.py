#!/usr/local/bin/python3

import random
import sys
from collections import Counter

def main():
	people = 5
	N = 10000
	resultList = []
	for i in range(N):
		resultList.append(test(people))
	result = Counter(resultList)
	for key, value in result.items():
		result[key] = value/N*100
	print (result)

def test(N):
	sample = [int(a/2) for a in range(0,2*N,1)];
	shuffled = random.shuffle(sample)
	count = 0
	for i in range(N):
		if sample[2*i] == sample[2*i+1]:
			count = count + 1
	return (str(count))

if __name__ == "__main__":
	main()